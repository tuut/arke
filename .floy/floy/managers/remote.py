import sys
from os.path import join
from time import strftime

from fabric.api import *
from fabric.colors import *
from fabric.contrib.files import upload_template as orig_upload_template
from fabric.contrib.files import contains, exists, is_link, sed
from fabric.contrib.project import upload_project

import floy as floy
from floy.helpers import *
from floy.managers.boilerplate import ManagerBoilerplate


class RemoteManager(ManagerBoilerplate):

  def setup(self):
    isInstalled = self.checkRequisites()
    sitesAvailable = ''
    sitesEnabled = ''

    if(isInstalled.has_key('nginx') and isInstalled['nginx']):
      installationMode = 'manual'

      sitesAvailable = join(floy.Core.paths['nginx'], 'sites-available',
                            floy.Core.getEnvOption('name'))
      sitesEnabled = join(floy.Core.paths['nginx'], 'sites-enabled', floy.Core.getEnvOption('name'))

      # nginx setup
      if(isInstalled.has_key('ee') and isInstalled['ee'] and ask('Create website with EasyEngine?')):
        installationMode = 'ee'
        typeFlags = ['html', 'php', 'mysql', 'wp', 'wpfc']

        print yellow('\n>> Creating site with EasyEngine')
        siteType = typeFlags[whichOption(['HTML', 'PHP', 'PHP \ MySQL',
                                          'Wordpress', 'Wordpress + FastCGI Cache'],
                                         'Choose a website type',
                                         'Type: ')]

        with hide('warnings'), settings(warn_only=True):
          sudo('ee site create --%s %s' %
               (siteType, floy.Core.getEnvOption('name')))

        with hideOutput():
          # Appends /current to the server block root path
          sed(sitesAvailable, 'root .*;', 'root %s;' % floy.Core.paths['webRoot'],
              limit='', use_sudo=True, backup='', flags='i', shell='/bin/bash')

          # Deletes default files
          if(len(floy.Core.paths['publicHTML']) > 0 and floy.Core.paths['publicHTML'] != '/'):
            sudo('rm -rf %s/*' % floy.Core.paths['publicHTML'])

        print green('>> Done creating site with EasyEngine')

      elif ask('Run nginx configuration setup instead?'):
        print yellow('\n>> Creating site with floy\'s nginx template')
        with hideOutput():
          print cyan('>>> Uploading nginx.conf -> shared/nginx.conf')
          put('%s/templates/nginx/nginx.conf' % floy.Core.paths['auxFiles'],
              join(floy.Core.paths['shared'], 'nginx.conf'), use_sudo=True)

          print cyan('>>> Uploading nginx server block -> etc/sites-available/%s' % floy.Core.getEnvOption('name'))
          self.upload_template('site',
                               sitesAvailable,
                               template_dir='%s/templates/nginx' % floy.Core.paths['auxFiles'],
                               use_sudo=True,
                               use_jinja=True,
                               context={
                                   'HOSTNAME': floy.Core.getEnvOption('hostnames'),
                                   'ROOT': floy.Core.paths['webRoot'],
                               })

          print cyan('>>> Linking sites-available -> sites-enabled')
          if is_link(sitesEnabled):
            sudo('unlink %s' % sitesEnabled)
          elif exists(sitesEnabled):
            sudo('rm -rf %s' % sitesEnabled)
          sudo('ln -sfv %s %s' % (sitesAvailable, sitesEnabled))

          self.service_reload('nginx')
        print green('>> Done creating site with floy\'s nginx template')

    # Creates shared/release directory structure
    print yellow('\n>> Creating shared and releases directories')
    with hideOutput():
      sudo('mkdir -p %s %s' % (floy.Core.paths['releases'],
                               join(floy.Core.paths['shared'], 'uploads')))
      sudo('touch %s/robots.txt' % floy.Core.paths['shared'])
    print green('>> Done creating shared and releases directories')

    if(installationMode == 'ee'):
      defaultWPConfig = '%s/wp-config.php' % floy.Core.paths['project']
      if(exists(defaultWPConfig)):
        print yellow('\n>> Moving EasyEngine\'s default wp-config.php to shared folder')
        with hideOutput():
          sudo('mv %s %s/' % (defaultWPConfig, floy.Core.paths['shared']))
        print green('>> Done moving default wp-config.php')

    # .env
    print ''
    if ask('Upload .env?'):
      print yellow('\n>> Uploading .env')
      with cd(floy.Core.paths['shared']), hideOutput():
        self.upload_template('dotenv',
                             '.env',
                             template_dir='%s/templates/wp/' % floy.Core.paths['auxFiles'],
                             use_sudo=True,
                             use_jinja=True,
                             context={
                                 'ENVIRONMENT': env.name,
                                 'MAIN_URL': floy.Core.getEnvOption('name')
                             })

        print cyan('>>> Generating salts on the .env file')
        with hideOutput(), settings(warn_only=True):
          run('wp dotenv salts regenerate')
        print green('>> Done uploading .env')

    elif ask('Upload wp-config.php?'):
      print yellow('\n>> Uploading wp-config.php')
      with cd(floy.Core.paths['shared']), hideOutput():
        self.upload_template('wp-config.php',
                             'wp-config.php',
                             template_dir='%s/templates/wp/' % floy.Core.paths['auxFiles'],
                             use_sudo=True,
                             use_jinja=True,
                             context={
                                 'ENVIRONMENT': env.name
                             })
      print green('>> Done uploading wp-config.php')

    self.fixPermissions()

  def checkRequisites(self):
    isInstalled = {}
    with hide('warnings', 'output'), settings(warn_only=True):
      # Check for nginx
      with hide('running'):
        isInstalled['nginx'] = run('which nginx').return_code == 0

      # Check for Composer
      with hide('running'):
        result = run('which composer')

      isInstalled['composer'] = result.return_code == 0

      print yellow('\n>> Checking for Composer')
      if not isInstalled['composer']:
        print yellow('\n>> Installing Composer')
        with cd('/tmp/'):
          run('curl https://getcomposer.org/installer -o /tmp/composer-setup.php')
          run('php /tmp/composer-setup.php')
          sudo('mv /tmp/composer.phar /usr/local/bin/composer')
          print green('>> Composer installed')
      else:
        print green('>> Composer already installed')

      # Check for WP-CLI
      print yellow('\n>> Checking for WP-CLI')
      with hide('running'):
        result = run('which wp')

      isInstalled['wp'] = result.return_code == 0

      if not isInstalled['wp']:
        print yellow('\n>> Installing WP-CLI')
        run('curl https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar -o /tmp/wp-cli.phar')
        run('chmod +x /tmp/wp-cli.phar')
        sudo('mv /tmp/wp-cli.phar /usr/local/bin/wp')
        run('wp package install aaemnnosttv/wp-cli-dotenv-command')
        run('wp package install sebastiaandegeus/wp-cli-salts-command')
        print green('>> WP-CLI installed')
      else:
        print green('>> WP-CLI already installed')

      # Check for easyengine
      print yellow('\n>> Checking for EasyEngine')
      with hide('running'):
        result = run('which ee')

      isInstalled['ee'] = result.return_code == 0

      if not isInstalled['ee'] and ask('Should install EasyEngine? '):
        print yellow('\n>> Installing EasyEngine')
        sudo('wget -qO ee rt.cx/ee && sudo bash ee')
        print green('>> EasyEngine installed')
      else:
        print green('>> EasyEngine already installed')
    print ''
    return isInstalled

  def deploy(self, branch):
    release_name = ''
    clone_from = ''

    if ask('You want to continue with deploy "%s" to "%s"?' % (branch, env.name)):
      release_name = '%s_%s' % (strftime('%Y-%m-%d_%H-%M-%S'), branch)
      print yellow('\n>> Creating new release')
      with hideOutput():
        lbash('git pull origin %s' % (branch))
        lbash('git tag -a "%s" -m "%s"' % (release_name, env.name))
        lbash('git push --tags')
      print green('>> Done creating new release')

      self.cloneRelease(release_name)
      self.afterDeploy(release_name)

  def cloneRelease(self, release_name):
    curReleaseDir = join(floy.Core.paths['releases'], release_name)

    print yellow('\n>> Cloning newest release on remote server')
    with hide('running'):
      run('git clone --branch "%s" %s "%s"' %
          (release_name, floy.Core.options['project']['repo'], curReleaseDir))
    print green('>> Done cloning newest release')

    print yellow('\n>> Creating links between shared files')
    for arr in floy.Core.options['project']['fileStructure']['shared']:

      if len(arr) == 1:
        arr = [arr[0], arr[0]]

      nodeOriginFullPath = join(curReleaseDir, arr[0])
      nodeTargetFullPath = join(floy.Core.paths['shared'], arr[1])

      print cyan('>>> Linking: current/%s -> shared/%s' % tuple(arr))
      with hideOutput():
        if is_link(nodeOriginFullPath):
          sudo('unlink %s' % (nodeOriginFullPath))
        elif exists(nodeOriginFullPath):
          run('rm -rf %s' % (nodeOriginFullPath))
        run('ln -sfv %s %s' % (nodeTargetFullPath, nodeOriginFullPath))
    print green('>> Done linking shared files and folders')

    print yellow('\n>> Sending all files/folders listed on "toUpload"')
    for arr in floy.Core.options['project']['fileStructure']['toUpload']:

      if len(arr) == 1:
        arr = [arr[0], arr[0]]

      nodeOriginFullPath = join(floy.Core.paths['base'], arr[0])
      nodeTargetFullPath = join(curReleaseDir, arr[1])

      print cyan('>>> Uploading: %s -> %s' % tuple(arr))
      with hideOutput():
        upload_project(local_dir=nodeOriginFullPath,
                       remote_dir=nodeTargetFullPath, use_sudo=True)
    print green('>> Done uploading files and folders')

  def afterDeploy(self, release_name):
    curReleaseDir = join(floy.Core.paths['releases'], release_name)

    with hideOutput(), settings(warn_only=True):
      print yellow('\n>> Restarting services')
      for service in floy.Core.getEnvOption('services')['toRestart']:
        self.service_restart(service)
      print green('>> Done restarting services')

      print yellow('\n>> Reloading services')
      for service in floy.Core.getEnvOption('services')['toReload']:
        self.service_reload(service)
      print green('>> Done reloading services')

      print yellow('\n>> Running after-deploy commands')
      runCommandList(floy.Core.options['project']['cmds']['afterDeploy'],
                     curReleaseDir,
                     False)
      print green('>> Done running after-deploy commands')

    # Links latest release to the current directory
    print yellow('\n>> Linking "current" directory to newest release')

    with hideOutput():
      if is_link(floy.Core.paths['current']):
        sudo('unlink %s' % (floy.Core.paths['current']))
      elif exists(floy.Core.paths['current']):
        sudo('rm -rf %s' % (floy.Core.paths['current']))

      sudo('ln -sfv %s %s' % (curReleaseDir, floy.Core.paths['current']))
      print green('>> Done linking "current" directory')

    self.fixPermissions()

    self.cleanup_releases(floy.Core.options['project']['maxReleases'])

  def fixPermissions(self, folderPath=0):
    if(folderPath == 0):
      folderPath = floy.Core.paths['project']

    print yellow('\n>> Fixing project\'s permissions at \'%s\'' % folderPath)
    with hide('everything'):
      sudo('chown -RfHh %s:%s %s' %
           (floy.Core.getEnvOption('webServerUser'), floy.Core.getEnvOption('webServerGroup'), folderPath))
      with cd(folderPath):
        sudo('find . -type d -print0 | xargs -0 chmod 0775')
        sudo('find . -type f -print0 | xargs -0 chmod 0664')
    print green('>> Done fixing permissions')

  def cleanup_releases(self, keep):
    print yellow('\n>> Removing old releases...')
    with hide('everything'):
      releases = self.list_releases()
      releases.sort(reverse=True)

      for release in releases[int(keep):]:
        release = release.strip()
        sudo('rm -rf %s/%s' % (floy.Core.paths['releases'], release))
    print green('>> Done removing old releases')

  def list_releases(self):
    with cd(floy.Core.paths['releases']):
      return run('ls -1 | sort').split('\n')

  def service_restart(self, name):
    print cyan('>>> Restarting %s' % name)
    sudo('service %s restart' % name)

  def service_reload(self, name):
    print cyan('>>> Reloading %s' % name)
    sudo('service %s reload' % name)

  def upload_template(self, src, dest, *args, **kwargs):
    orig_upload_template(src, dest, *args, **kwargs)
    sudo('chmod +r %s' % dest)
