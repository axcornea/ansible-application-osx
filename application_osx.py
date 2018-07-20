#!/usr/bin/python

import os
import os.path
import subprocess as sp
import random
import string
from ansible.module_utils.basic import AnsibleModule


def sh(cmd):
    # TODO: redirect output to /dev/null
    return sp.check_call(cmd, shell=True)


def random_string(n=16):
    return ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=16))


class ApplicationInstallationError(Exception):
    pass


class OSXApplication:
    
    def __init__(self, name=None, root_dir='/Applications'):
        self.name = name
        self.root_dir = root_dir

    @property
    def is_installed(self):
        if not hasattr(self, '__installed'):
            self.__installed = (self.name + ".app") in os.listdir(self.root_dir) 
        return self.__installed

    def __install_dmg(self, src):
        mountpoint = '/tmp/' + random_string()        
        rc = sh('hdiutil mount {} -noverify -noautofsck -mountpoint {}'.format(src, mountpoint))
        if rc != 0:
            raise ApplicationInstallationError('Error occurred while mounting "%s"!' % src)

        found = True
        for f in os.listdir(mountpoint):
            if f.endswith('.pkg'):
                self.__install_pkg(mountpoint + '/' + f)
                break
            elif f.endswith('.app'):
                self.__install_dmg_app(mountpoint + '/' + f)
                break
        else:
            found = False

        if sh('hdiutil unmount ' + mountpoint) != 0:
            raise ApplicationInstallationError('Error occurred while unmounting "%s"!' % mountpoint)
        if not found:
            raise ApplicationInstallationError('No package found in "%s" image!' % src)

    def __install_dmg_app(self, src):
        rc = sh('cp -r {src} {dest}'.format(
            src=src,
            dest=self.root_dir
        ))
        if rc != 0:
            raise ApplicationInstallationError('Cannot copy directory!')

    def __install_pkg(self, src): 
        rc = sh('installer -src {src} -target {root_dir}'.format(
            src=src,
            root_dir=self.root_dir
        ))
        if rc != 0:
            raise ApplicationInstallationError('Error occurred in installer')

    def install(self, src):
        if self.is_installed:
            return

        if src.endswith('.dmg'):
            self.__install_dmg(src)
        elif src.endswith('.pkg'):
            self.__install_pkg(src)
        else:
            raise ApplicationInstallationError('Unkown package format!')

    def uninstall(self):
        if not self.is_installed:
            return

        if sh('rm -rf {root_dir}/{app_name}.app'.format(root_dir=self.root_dir, app_name=self.name)) != 0:
            raise ApplicationInstallationError('Error while uninstalling application!')


if __name__ == '__main__':
    module = AnsibleModule(argument_spec=dict(
        name=dict(required=True),
        path=dict(aliases=['src']),
        user=dict(),
        state=dict(required=True, choices=['present', 'absent'])
    ), supports_check_mode=True)

    result = {'changed': False}
    
    if not os.path.isfile(module.params['path']):
        module.fail_json(msg='File "%s" does not exists!' % module.params['path'])

    if module.params['user'] != None:
        app = OSXApplication(module.params['name'], root_dir=("~%s/Applications" % module.params['user']))
    else:
        app = OSXApplication(module.params['name'], root_dir='/Applications')

    if module.params['state'] == 'present' and not app.is_installed:
        if not module.check_mode:
            app.install(module.params['src'])
        result['changed'] = True
    elif module.params['state'] == 'absent' and app.is_installed:
        if not module.check_mode:
            app.uninstall()
        result['changed'] = True

    module.exit_json(**result)
