#
# Kosmos Builder
# Copyright (C) 2020 Nichole Mattera
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 
# 02110-1301, USA.
#

import common
import config
from github import Github
from gitlab import Gitlab
import json
import os
import re
import shutil
import urllib.request
import uuid
import zipfile

gh = Github(config.github_username, config.github_password)
gl = Gitlab('https://gitlab.com', private_token=config.gitlab_private_access_token)
gl.auth()

def get_latest_release(module):
    if common.GitService(module['git']['service']) == common.GitService.GitHub:
        try:
            repo = gh.get_repo(f'{module["git"]["org_name"]}/{module["git"]["repo_name"]}')
        except:
            print(f'[Error] Unable to find repo: {module["git"]["org_name"]}/{module["git"]["repo_name"]}')
            return None
        
        releases = repo.get_releases()
        if releases.totalCount == 0:
            print(f'[Error] Unable to find any releases for repo: {module["git"]["org_name"]}/{module["git"]["repo_name"]}')
            return None
        
        return releases[0]
    else if common.GitService(module['git']['service']) == common.GitService.GitLab:
        try:
            project = gl.projects.get(f'{module["git"]["org_name"]}/{module["git"]["repo_name"]}')
        except:
            print(f'[Error] Unable to find repo: {module["git"]["org_name"]}/{module["git"]["repo_name"]}')
            return None

        tags = project.tags.list()
        for tag in tags:
            if tag.release is not None:
                return tag

        print(f'[Error] Unable to find any releases for repo: {module["git"]["org_name"]}/{module["git"]["repo_name"]}')
        return None
    else:
        # TODO: SourceForge

def download_asset(module, release, index):
    pattern = module['git']['asset_patterns'][index]

    if common.GitService(module['git']['service']) == common.GitService.GitHub:
        if release is None:
            return None
        
        matched_asset = None
        for asset in release.get_assets():
            if re.search(pattern, asset.name):
                matched_asset = asset
                break

        if matched_asset is None:
            print(f'[Error] Unable to find asset that match pattern: "{pattern}"')
            return None

        download_path = common.generate_temp_path()
        urllib.request.urlretrieve(matched_asset.browser_download_url, download_path)

        return download_path
    else if common.GitService(module['git']['service']) == common.GitService.GitLab:
        group = module['git']['group']

        match = re.search(pattern, release.release['description'])
        if match is None:
            return None

        groups = match.groups()
        if len(groups) <= group:
            return None

        download_path = common.generate_temp_path()
        urllib.request.urlretrieve(f'https://gitlab.com/{module["git"]["org_name"]}/{module["git"]["repo_name"]}{groups[group]}', download_path)

        return download_path
    else:
        # TODO: SourceForge

def find_asset(release, pattern):
    for asset in release.get_assets():
        if re.search(pattern, asset.name):
            return asset

    return None

def download_haxchi(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(temp_directory)

    common.delete_path(bundle_path)

    return release.tag_name

def download_hid_to_vpad(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(temp_directory)

    common.delete_path(bundle_path)

    return release.tag_name

def download_hb_appstore(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    common.mkdir(os.path.join(temp_directory, 'wiiu', 'apps', 'appstore'))
    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(temp_directory, 'wiiu', 'apps', 'appstore'))
    
    common.delete_path(bundle_path)

    return release.name

def download_homebrew_launcher(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    app_path = download_asset(module, release, 0)
    if app_path is None:
        return None

    with zipfile.ZipFile(app_path, 'r') as zip_ref:
        zip_ref.extractall(temp_directory)

    common.delete_path(app_path)

    channel_path = download_asset(module, release, 1)
    if channel_path is None:
        return None

    common.mkdir(os.path.join(temp_directory, 'install', 'hbc'))
    with zipfile.ZipFile(channel_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(temp_directory, 'install', 'hbc'))

    common.delete_path(channel_path)

    return release.tag_name

def download_jstypehax(module, temp_directory, kosmos_version, kosmos_build):
    common.mkdir(os.path.join(temp_directory, 'wiiu'))
    common.copy_module_file('jstypehax', 'payload.elf', os.path.join(temp_directory, 'wiiu', 'payload.elf'))
    return 'latest'

def download_mocha(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    common.mkdir(os.path.join(temp_directory, 'wiiu', 'apps', 'mocha'))
    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(temp_directory, 'wiiu', 'apps', 'mocha'))

    common.delete_path(bundle_path)
    common.copy_module_file('mocha', 'config.ini', os.path.join(temp_directory, 'wiiu', 'apps', 'mocha', 'config.ini'))
    common.copy_module_file('mocha', 'icon.png', os.path.join(temp_directory, 'wiiu', 'apps', 'mocha', 'icon.png'))
    common.copy_module_file('mocha', 'meta.xml', os.path.join(temp_directory, 'wiiu', 'apps', 'mocha', 'meta.xml'))

    return release.tag_name

def download_nanddumper(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(temp_directory)

    common.delete_path(bundle_path)

    return release.tag_name

def download_savemii(module, temp_directory, kosmos_version, kosmos_build):
    release = get_latest_release(module)
    bundle_path = download_asset(module, release, 0)
    if bundle_path is None:
        return None

    common.mkdir(os.path.join(temp_directory, 'wiiu', 'apps'))
    with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(temp_directory, 'wiiu', 'apps'))

    common.delete_path(bundle_path)

    return release.tag_name

def download_wup_installer_gx2(module, temp_directory, kosmos_version, kosmos_build):
    # TODO: Figure out SourceForge...

def build(temp_directory, kosmos_version, kosmos_build, auto_build):
    results = []

    # Open up modules.json
    with open('modules.json') as json_file:
        # Parse JSON
        data = json.load(json_file)

        # Loop through modules
        for module in data:
            sdsetup_opts = module['sdsetup']

            # Running a Kosmos Build
            if kosmos_build:
                # Download the module.
                print(f'Downloading {module["name"]}...')
                download = globals()[module['download_function_name']]
                version = download(module, temp_directory, kosmos_version, kosmos_build)
                if version is None:
                    return None
                results.append(f'  {module["name"]} - {version}')

            # Running a SDSetup Build
            elif not kosmos_build and sdsetup_opts['included']:
                # Only show prompts when it's not an auto build.
                if not auto_build:
                    print(f'Downloading {module["name"]}...')

                # Make sure module directory is created.
                module_directory = os.path.join(temp_directory, sdsetup_opts['name'])
                common.mkdir(module_directory)

                # Download the module.
                download = globals()[module['download_function_name']]
                version = download(module, module_directory, kosmos_version, kosmos_build)
                if version is None:
                    return None

                # Auto builds have a different prompt at the end for parsing.
                if auto_build:
                    results.append(f'{sdsetup_opts["name"]}:{version}')
                else:
                    results.append(f'  {module["name"]} - {version}')
    
    return results
