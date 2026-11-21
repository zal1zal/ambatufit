"""Start isolated local services and execute the actual client HTTP smoke script.

Only explicit smoke tooling knows the other package's location. Neither service
nor frontend runtime imports the other package. No existing DB/.env is changed.
"""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def unused_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    with tempfile.TemporaryDirectory(prefix='ambatufit-smoke-') as directory:
        core_port, integration_port = unused_port(), unused_port()
        env = {**os.environ, 'APP_ENV': 'test', 'DATABASE_URL': f'sqlite:///{Path(directory).as_posix()}/synthetic.db',
               'JWT_SECRET': secrets.token_urlsafe(48), 'INTEGRATION_API_TOKEN': secrets.token_urlsafe(32),
               'AI_INFERENCE_URL': '', 'INTEGRATION_MODE': 'live', 'PARTNER_CONTRACTS_CONFIRMED': 'false',
               'NUTRITION_PROVIDER_BASE_URL': '', 'GYM_PROVIDER_BASE_URL': '',
               'INTEGRATION_API_BASE_URL': f'http://127.0.0.1:{integration_port}/integration/v1',
               'EXPO_PUBLIC_API_BASE_URL': f'http://127.0.0.1:{core_port}/api/v1',
               'EXPO_PUBLIC_INTEGRATION_API_BASE_URL': f'http://127.0.0.1:{integration_port}/integration/v1',
               'AMBATUFIT_ALLOW_SYNTHETIC_WRITES': 'true'}
        # Seed prints synthetic demo credentials, so suppress routine setup output.
        subprocess.run([sys.executable, 'scripts/seed_demo.py'], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
        processes = []
        try:
            for module, port in [('app.main:app', core_port), ('integration.server:app', integration_port)]:
                process = subprocess.Popen([sys.executable, '-m', 'uvicorn', module, '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                processes.append(process)
                for attempt in range(60):
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read().decode())
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1):
                            break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError(f'Local service did not start: {module}')
            completed = subprocess.run(['node', str(ROOT.parent / 'frontend/scripts/smoke-api.js')], cwd=ROOT.parent / 'frontend', env=env)
            if completed.returncode:
                raise RuntimeError('Frontend HTTP smoke failed')
        finally:
            for process in processes:
                process.terminate()
                process.wait(timeout=10)
            # Give Uvicorn/SQLAlchemy worker threads time to close SQLite handles
            # before TemporaryDirectory removes the database on Windows.
            from urllib.error import URLError
            for _ in range(40):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{core_port}/health', timeout=0.2):
                        time.sleep(0.1)
                except (URLError, OSError):
                    break
            time.sleep(0.25)


if __name__ == '__main__':
    main()
