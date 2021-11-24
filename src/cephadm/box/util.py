from typing import Dict, List
import argparse
import subprocess
import os
import sys

class Config:
    args = {}

    @staticmethod
    def get(key):
        if key in Config.args:
            return Config.args[key]
        return None

    @staticmethod
    def add_args(args: Dict[str, str]) -> argparse.ArgumentParser:
        Config.args.update(args)

def ensure_outside_container(func) -> bool:
    def wrapper(*args, **kwargs):
        if not inside_container():
            return func(*args, **kwargs)
        else:
            raise RuntimeError('This command should be ran outside a container')
    return wrapper
    
def ensure_inside_container(func) -> bool:
    def wrapper(*args, **kwargs):
        if inside_container():
            return func(*args, **kwargs)
        else:
            raise RuntimeError('This command should be ran inside a container')
    return wrapper


def run_shell_command(command: str, expect_error=False) -> str:
    if Config.get('verbose'):
        print(f'Running command: {command}')
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out = ''
    # let's read when output comes so it is in real time
    while True:
        # TODO: improve performance of this part, I think this part is a problem
        pout = process.stdout.read(1).decode('latin1') 
        if pout == '' and process.poll() is not None:
            break
        if pout:
            if Config.get('verbose'):
                sys.stdout.write(pout)
                sys.stdout.flush()
            out += pout
    process.wait()

    # no last break line
    err = process.stderr.read().decode().rstrip() # remove trailing whitespaces and new lines
    out = out.strip()

    if process.returncode != 0 and not expect_error:
        raise RuntimeError(f'Failed command: {command}\n{err}')
        sys.exit(1)
    return out

@ensure_inside_container
def run_cephadm_shell_command(command: str, expect_error=False) -> str:
    out = run_shell_command(f'cephadm shell -- {command}', expect_error)
    return out

def run_dc_shell_command(command: str, index: int, box_type: str, expect_error=False) -> str:
    out = run_shell_command(f'docker-compose exec --index={index} {box_type} {command}', expect_error)
    return out

def inside_container() -> bool:
    return os.path.exists('/.dockerenv')

@ensure_outside_container
def get_host_ips() -> List[List[str]]:
    containers_info = get_boxes_container_info()
    print(containers_info)
    ips = []
    for container in containers_info:
        if container[1][:len('box_hosts')] == 'box_hosts':
            ips.append(container[0])
    return ips
    
@ensure_outside_container
def get_boxes_container_info() -> List[List[str]]:
        ips_query = "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}} %tab% {{.Name}} %tab% {{.Config.Hostname}}' $(docker ps -aq) | sed 's#%tab%#\t#g' | sed 's#/##g' | sort -t . -k 1,1n -k 2,2n -k 3,3n -k 4,4n"
        out = run_shell_command(ips_query)
        info = []
        for line in out.split('\n'):
            container = line.split()
            if container[1].strip()[:4] == 'box_':
                info.append(container)
        return info
    

