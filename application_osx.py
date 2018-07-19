#!/usr/bin/python

import os
import subprocess as sp
import random
import string
from ansible.module_utils.basic import AnsibleModule


def sh(cmd):
    # TODO: redirect output to /dev/null
    return sp.check_call(cmd, shell=True)


def random_string(n=16):
    return ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=16))


class OSXApplication:
    
    def __init__(self, name=None, root_dir='/Applications'):
        self.name = name
        self.root_dir = root_dir

    @property
    def is_installed(self):
        self.__installed = (self.name + ".app") in os.listdir(self.root_dir) 
        return self.__installed

    def __install_dmg(self, src):
        mountpoint = '/tmp/' + random_string()        
        rc = sh('hdiutil mount {} -noverify -noautofsck -mountpoint {}'.format(src, mountpoint))
        if rc != 0: return False

        for f in os.listdir(mountpoint):
            if f.endswith('.pkg'):
                ok = self.__install_pkg(mountpoint + '/' + f)
                return ok
            elif f.endswith('.app'):
                ok = self.__install_dmg_app(mountpoint + '/' + f)
                return ok
        
        return False

    def __install_dmg_app(self, src):
        rc = sh('cp -r {src} {dest}'.format(
            src=src,
            dest=self.root_dir
        ))
        return rc == 0

    def __install_pkg(self, src): 
        rc = sh('installer -src {src} -target {root_dir}'.format(
            src=src,
            root_dir=self.root_dir
        ))
        return rc == 0

    def install(self, src):
        if self.__installed: return

        if src.endswith('.dmg'):
            ok = self.__install_dmg(src)
        elif src.endswith('.pkg'):
            ok = self.__install_pkg(src)
        
        return ok

    def uninstall(self):
        if not self.__installed: return
        sh('rm -rf {root_dir}/{app_name}.app'.format(root_dir=self.root_dir, app_name=self.name))


if __name__ == '__main__':
    module = AnsibleModule(argument_spec=dict(
        name=dict(required=True),
        path=dict(required=True, aliases=['src']),
        user=dict(),
        state=dict(choices=['present', 'absent'])
    ), supports_check_mode=True)

    result = {'changed': False}
    
    if module.params['user'] != None:
        app = OSXApplication(module.params['name'], root_dir=("~%s/Applications" % module.params['user']))
    else:
        app = OSXApplication(module.params['name'])

    if module.params['state'] == 'present' and not app.is_installed:
        if not module.check_mode:
            ok = app.install(module.params['src'])
            if not ok:
                module.fail_json(msg="Cannot install")
        result['changed'] = True
    elif module.params['state'] == 'absent' and app.is_installed:
        if not module.check_mode:
            ok = app.uninstall()
            if not ok:
                module.fail_json(msg="Cannot uninstall")
        result['changed'] = True

    module.exit_json(**result)
