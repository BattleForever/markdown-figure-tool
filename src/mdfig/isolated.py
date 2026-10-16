"""A cancellable rendering service with an enforced deadline outside the browser."""
from dataclasses import asdict
from pathlib import Path
import json
import os
import sys
import tempfile
import time

from .parser import Figure
from .processes import ProcessOwner
from .renderer import RenderOptions, RenderSession


def atomic_json(path, data):
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    os.replace(pending, path)


def read_json(path):
    """Retry only a transient Windows sharing/permission denial, for at most .5s."""
    deadline = time.monotonic() + 0.5
    while True:
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.025)


class IsolatedRenderer:
    def __init__(self, options=None, cancelled=lambda: False, job_root=None):
        self.options = options or RenderOptions()
        self.cancelled = cancelled
        self.job_root = job_root
        self.owner = None
        self.temporary = None
        self.directory = None
        self.sequence = 0
        self.startup_failure = None
        self.cleanup_warnings = []
        self.browser_name = '独立渲染进程（按需启动）'

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()

    def wait_json(self, path, deadline):
        while True:
            if self.cancelled():
                self.stop(force=True)
                raise RuntimeError('转换已取消。')
            if path.is_file():
                return read_json(path)
            if self.owner.process.poll() is not None:
                code = self.owner.process.returncode
                self.stop(force=True)
                raise RuntimeError(f'渲染子进程异常退出（{code}），原代码已保留。')
            if time.monotonic() >= deadline:
                self.stop(force=True)
                raise TimeoutError('图形渲染超过时间限制，已停止本程序的渲染进程；原代码保留。')
            time.sleep(0.04)

    def start(self):
        if self.startup_failure:
            raise RuntimeError(self.startup_failure)
        if self.owner:
            return
        if self.job_root:
            Path(self.job_root).mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='render-', dir=self.job_root)
        self.directory = Path(self.temporary.name)
        atomic_json(self.directory / 'options.json', asdict(self.options))
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--renderer-worker', str(self.directory)]
        else:
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'launcher.py'), '--renderer-worker', str(self.directory)]
        try:
            self.owner = ProcessOwner(command)
            ready = self.wait_json(self.directory / 'ready.json', time.monotonic() + 30)
            if ready.get('error'):
                raise RuntimeError(ready['error'])
            self.browser_name = ready['browser']
        except Exception as error:
            if not self.cancelled():
                self.startup_failure = str(error)
            self.stop()
            raise
        except BaseException:
            self.stop()
            raise

    def render(self, figure, source_dir, output):
        self.start()
        self.sequence += 1
        sequence = self.sequence
        response_path = self.directory / f'response-{sequence}.json'
        request = {'figure': asdict(figure), 'source_dir': str(source_dir), 'output': str(output)}
        atomic_json(self.directory / f'request-{sequence}.json', request)
        response = self.wait_json(response_path, time.monotonic() + max(2, self.options.timeout_ms / 1000 + 2))
        if response.get('error'):
            if response.get('restart'):
                self.stop()
            raise RuntimeError(response['error'])
        return response['result']

    def stop(self, force=False):
        if self.owner:
            if not force and self.directory and self.owner.process.poll() is None:
                try:
                    atomic_json(self.directory / 'stop.json', {})
                    self.owner.process.wait(timeout=1.5)
                except (OSError, TimeoutError):
                    pass
                except Exception:
                    pass
            self.owner.stop()
            self.owner = None
        if self.temporary:
            temporary = self.temporary
            self.temporary = None
            until = time.monotonic() + 2
            while True:
                try:
                    temporary.cleanup()
                    break
                except OSError as error:
                    if time.monotonic() >= until:
                        # An external scanner can hold files beyond our process
                        # lifetime. Preserve its exact owned path for diagnosis,
                        # rather than turning a cleanup warning into a GUI failure.
                        self.cleanup_warnings.append({'path': temporary.name, 'error': str(error)})
                        break
                    time.sleep(0.05)
        self.directory = None
        self.sequence = 0


def serve(directory):
    directory = Path(directory).resolve()
    options = RenderOptions(**read_json(directory / 'options.json'))
    # Keep browser profiles/download scratch data in this owned task directory,
    # so a forcibly stopped script cannot leave profiles in the user's Temp.
    scratch = directory / 'browser-temp'
    scratch.mkdir()
    os.environ['TMP'] = str(scratch)
    os.environ['TEMP'] = str(scratch)
    tempfile.tempdir = str(scratch)
    try:
        with RenderSession(options) as renderer:
            atomic_json(directory / 'ready.json', {'browser': renderer.browser_name})
            sequence = 1
            while directory.is_dir():
                if (directory / 'stop.json').is_file():
                    return 0
                path = directory / f'request-{sequence}.json'
                if not path.is_file():
                    time.sleep(0.03)
                    continue
                try:
                    request = read_json(path)
                    figure = Figure(**request['figure'])
                    result = renderer.render(figure, Path(request['source_dir']), Path(request['output']))
                    response = {'result': result}
                except Exception as error:
                    response = {'error': str(error), 'restart': not renderer.browser.is_connected()}
                atomic_json(directory / f'response-{sequence}.json', response)
                sequence += 1
    except Exception as error:
        if directory.is_dir():
            atomic_json(directory / 'ready.json', {'error': str(error)})
        return 1
    return 0
