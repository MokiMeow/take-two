"""Stage the fixed renderer in data, keeping all bundles/dependency writes there."""
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def prepare() -> Path:
    target=ROOT/'data/renderer-runtime'
    target.mkdir(parents=True,exist_ok=True)
    for directory in ('src','public'):
        shutil.copytree(ROOT/'render'/directory,target/directory,dirs_exist_ok=True)
    for filename in ('cli.mjs','package.json','package-lock.json','tsconfig.json'):
        shutil.copy2(ROOT/'render'/filename,target/filename)
    if not (target/'node_modules/@remotion/renderer/package.json').exists():
        npm=shutil.which('npm.cmd') or shutil.which('npm')
        if not npm:
            raise RuntimeError('npm is required for the project-local renderer')
        subprocess.run([npm,'ci','--cache',str(ROOT/'data/npm-cache'),'--no-audit','--no-fund'],cwd=target,check=True,timeout=300)
    # Reuse the installed headless browser without modifying the renderer source.
    browser=ROOT/'render/node_modules/.remotion'
    if browser.exists():
        shutil.copytree(browser,target/'node_modules/.remotion',dirs_exist_ok=True)
    return target/'cli.mjs'


if __name__=='__main__':
    print('Prepared renderer:',prepare())
