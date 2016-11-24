#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import hashlib, json, random, os, sys, time, subprocess
import cgi, netaddr

xform = cgi.FieldStorage();

# Check that this is GitHub calling
from netaddr import IPNetwork, IPAddress
GitHubNetwork = IPNetwork("192.30.252.0/22") # TBD!
callerIP = IPAddress(os.environ['REMOTE_ADDR'])
if not callerIP in GitHubNetwork:
    print("Status: 401 Unauthorized\r\nContent-Type: text/plain\r\n\r\nI don't know you!\r\n")
    sys.exit(0)


def getvalue(key):
    val = xform.getvalue(key)
    if val:
        return val
    else:
        return None

jsin = getvalue('payload')
data = json.loads(jsin)

if 'repository' in data and 'name' in data['repository']:
    reponame = data['repository']['name']
    pusher = data['pusher']['name']
    ref = data['ref']
    before = data['before']
    after = data['after']
    broken = False
    
    # Unless asfgit is the pusher, we need to act on this.
    if pusher != 'asfgit' and os.path.exists("/x1/repos/asf/%s.git" % reponame):
        ########################
        # Get ASF ID of pusher #
        ########################
        asfid = pusher # We don't know how to fetch it yet
        
        ##################
        # Write Push log #
        ##################
        open("/x1/pushlogs/%s.txt" % reponame, "a").write(
            "[%s] %s -> %s (%s@apache.org / %s)\n" % (
                time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                before,
                after,
                asfid,
                pusher
                )
            )
        
        #######################################
        # Check that we haven't missed a push #
        #######################################
        if before:
            try:
                subprocess.check_call(['git','cat-file','-e', before])
            except:
                pass # TODO: Add notification thing for infra or PMC
        
        ####################
        # SYNC WITH GITHUB #
        ####################
        log = "[%s] [%s.git]: Got a sync call for %s.git, pushed by %s\n" % (time.strftime("%c"), reponame, reponame, asfid)
        try:
            # Change to repo dir
            os.chdir("/x1/repos/asf/%s.git" % reponame)
            # Run 'git fetch'
            out = subprocess.check_call(["git", "fetch"])
            log += "[%s] [%s.git]: Git fetch succeeded\n" % (time.strftime("%c"), reponame)
            try:
                os.unlink("/x1/gitbox/broken/%s.txt" % cfg.repo_name)
            except:
                pass
        except Exception as err:
            broken = True
            log += "[%s] [%s.git]: Git fetch failed: %s\n" % (time.strftime("%c"), reponame, err)
            with open("/x1/gitbox/broken/%s.txt" % cfg.repo_name, "w") as f:
                f.write("BROKEN AT %s\n" % time.strftime("%c"))
                f.close()
        open("/x1/gitbox/sync.log", "a").write(log)
        
        
        #####################################
        # Deploy commit mails via multimail #
        #####################################
        if not Broken: # only fire this off if the sync succeeded
            log = "[%s] [%s.git]: Got a multimail call for %s.git, triggered by %s\n" % (time.strftime("%c"), reponame, reponame, asfid)
            try:
                # Change to repo dir
                os.chdir("/x1/repos/asf/%s.git" % reponame)
                # set some vars
                os.environ['NO_SYNC'] = 'yes'
                os.environ['WEB_HOST'] = "https://gitbox.apache.org/"
                os.environ['GIT_COMMITTER_NAME'] = asfid
                os.environ['GIT_COMMITTER_EMAIL'] = "%s@apache.org" % asfid
                os.environ['GIT_PROJECT_ROOT'] = "/x1/repos/asf/" + reponame + ".git"
                os.environ['PATH_INFO'] = reponame + '.git'
                hook = "/x1/repos/asf/" + reponame + ".git"
                if not hook.endswith('.git'): hook += '/.git'
                hook += '/hooks/post-receive'
            
                # If we found the hook, prep to run it
                if os.path.exists(hook):
                    update = "%s %s %s\n" % (before, after, ref)
                    cwd = os.getcwd()
                    # Fire off the email hook
                    os.chdir("/x1/repos/asf/" + reponame + ".git")
                    process = Popen([hook], stdin=PIPE, stdout=PIPE, stderr=PIPE, env=os.environ)
                    process.communicate(input=update)
                    log += "[%s] [%s.git]: Multimail deployed!\n" % (time.strftime("%c"), reponame)
                      
            except Exception as err:
                log += "[%s] [%s.git]: Multimail hook failed: %s\n" % (time.strftime("%c"), reponame, err)
            open("/x1/gitbox/sync.log", "a").write(log)

print("Status: 204 Message received\r\n\r\n")