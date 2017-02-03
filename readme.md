# Floy documentation

## Requirements
* [Fabric](https://get.fabric.io/)
* [Jinja2](http://jinja.pocoo.org/)
* [Floy](https://github.com/tuut/floy)
* A [SSH Config](http://nerderati.com/2011/03/17/simplify-your-life-with-an-ssh-config-file/)
* A deployable project

## Usage

```
fab {environment} {task} [-u {user}] [-p {password}]


Local-only:

fab local setup
fab local install
fab local reset
fab local import_db
fab local git:setup
fab local wp:configure


Remote-only:

fab {environment} setup
fab {environment} deploy
fab {environment} checkRequisites
fab {environment} fixPermissions
fab {environment} cleanup_releases
fab {environment} service_restart
fab {environment} service_reload
```

## Documentation

### `floy.json` example

```json
{
  "project": {
    "repo": "git@github.com:user/repo.git",
    "type": "bedrock-wordpress",
    "fileStructure": {
      "shared": [
        ["robots.txt"],
        [".htaccess"],
        [".env"],
        ["web/app/uploads", "uploads"]
      ],
      "toUpload": [
        ["web/app/themes/sepha/dist", "web/app/themes/sepha/"]
      ]
    },
    "cmds": {
      "install": [
        ["", "composer install"],
        ["web/app/themes/sepha", "composer install"]
      ],
      "afterDeploy": [
        ["", "rm -rf fabfile.py floy.json readme.md .editorconfig"],
        ["", "composer install"],
        ["web/app/themes/sepha", "composer install"]
      ],      
    },
    "maxReleases": 5
  },
  "hosts": {
    "production": {
      "hosts": ["127.0.0.1"],
      "name": "example.staging.com",
      "projectDir": "/var/www",
      "projectPublicDir": "",
      "webRootDir": "web",
      "hostnames": "example.staging.com www.example.staging.com",
      "webServerUser": "www-data",
      "webServerGroup": "www-data",
      "services": {
        "toRestart": ["php5-fpm"],
        "toReload": ["nginx"]
      }
    }
  }
}
```

#### Project configuration

<table style="width: 100%">
  <tr>
    <th>
      Field
    </th>
    <th>
      Description
    </th>
  </tr>
  <tr>
    <td>repo</td>
    <td>The project's repository url</td>
  </tr>
  <tr>
    <td>type</td>
    <td>The project's type.
    <br><br>
    <strong>Available options:</strong> html, php, simple-wordpress, bedrock-wordpress</td>
  </tr>
  <tr>
    <td>fileStructure.shared</td>
    <td>A list of symbolic links to be created after each deploy. You can set a different name for the link by passing a second string to the link array. See example above.
    <br><br>
    <strong>Syntax:</strong> [projectPath, sharedPath]
    <br><br>
    <strong>Examples:</strong>
    <br><br>
    ['robots.txt'] creates a link on the project's root directory to a robots.txt file on the root of the project's shared folder.
    <br>
    <br>
    ["web/app/uploads", "uploads"] creates a links on the projects web/app/ directory to a uploads directory on the root of the project's shared folder.
    </td>
  </tr>
  <tr>
    <td>fileStructure.toUpload</td>
    <td>A list of files/directories to be uploaded after each deploy. Useful for built files.
    <br><br>
    <strong>Syntax:</strong> [localPath, remotePath]
    <br><br>
    <strong>Examples:</strong>
    <br><br>
    ["web/app/themes/sepha/dist", "web/app/themes/sepha/"] uploads the local dist folder to the remote web/app/themes/sepha/ directory.
    </td>
  </tr>
  <tr>
    <td>cmds.install</td>
    <td>A list of commands to be executed when 'fab local install' is executed.
    <br><br>
    <strong>Syntax:</strong> [executionPath, commandString]
    <br><br>
    <strong>Examples:</strong>
    <br><br>
    ["", "composer install"] runs a composer install on the project's root.
    <br><br>
    ["web/app/themes/sepha", "composer install"] runs a composer install on the web/app/themes/sepha directory.
    </td>
  </tr>
  <tr>
    <td>cmds.afterDeploy</td>
    <td>A list of commands to be executed after each successfull deploy. Can use sudo.
    <br><br>
    <strong>Syntax:</strong> [executionPath, commandString]
    <br><br>
    <strong>Examples:</strong>
    <br><br>
    ["", "rm -rf fabfile.py floy.json readme.md .editorconfig"] runs a rm command on the project's root.
    <br><br>
    ["web/app/themes/sepha", "composer install"] runs a composer install on the web/app/themes/sepha directory.
    </td>
  </tr>
  <tr>
    <td>maxReleases</td>
    <td>Number of releases to keep on the remote server.</td>
  </tr>
</table>

#### Host(s) configuration

<table style="width: 100%">
  <tr>
    <th>
      Field
    </th>
    <th>
      Description
    </th>
  </tr>
  <tr>
    <td>hosts</td>
    <td>A list of the server ips/hostnames</td>
  </tr>
  <tr>
    <td>name</td>
    <td>The project name. Used to create the server folder.</td>
  </tr>
  <tr>
    <td>projectDir</td>
    <td>The project folder directory.
    <br><br>
    <strong>Example:</strong> /var/www
    </td>
  </tr>
  <tr>
    <td>projectPublicDir</td>
    <td>The project public html directory.
    <br><br>
    Relative to {projectDir}/{name}.
    </td>
  </tr>
  <tr>
    <td>webRootDir</td>
    <td>The project website directory.
    <br><br>
    Relative to {projectDir}/{name}/{projectPublicDir}. Can be an empty string.</td>
  </tr>
  <tr>
    <td>hostnames</td>
    <td>The project hostnames that nginx will listen to. Can be overwritten in @task {environment}.</td>
  </tr>
  <tr>
    <td>webServerUser</td>
    <td>User for nginx/apache (usually www-data)</td>
  </tr>
  <tr>
    <td>webServerGroup</td>
    <td>User for nginx/apache (usually www-data)</td>
  </tr>
  <tr>
    <td>services.toRestart</td>
    <td>Server's services to restart after each deploy.</td>
  </tr>
  <tr>
    <td>services.toReload</td>
    <td>Server's services to reload after each deploy</td>
  </tr>
</table>
