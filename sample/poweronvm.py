#!/usr/bin/python
#
# VMware vSphere Python SDK
# Copyright (c) 2008-2013 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Python program for powering on vms on a host on which hostd is running
"""

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl

import argparse
import atexit
import sys

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """

   parser = argparse.ArgumentParser(description='Process args for powering on a Virtual Machine')
   parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
   parser.add_argument('-o', '--port', required=True, action='store', help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store', help='Password to use when connecting to host')
   parser.add_argument('-v', '--vmname', required=True, action='append', help='Names of the Virtual Machines to power on')
   args = parser.parse_args()
   return args

def WaitForTasks(tasks, si):
   """
   Given the service instance si and tasks, it returns after all the
   tasks are complete
   """

   pc = si.content.propertyCollector

   taskList = [str(task) for task in tasks]

   # Create filter
   objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                                                            for task in tasks]
   propSpec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                         pathSet=[], all=True)
   filterSpec = vmodl.query.PropertyCollector.FilterSpec()
   filterSpec.objectSet = objSpecs
   filterSpec.propSet = [propSpec]
   filter = pc.CreateFilter(filterSpec, True)

   try:
      version, state = None, None

      # Loop looking for updates till the state moves to a completed state.
      while len(taskList):
         update = pc.WaitForUpdates(version)
         for filterSet in update.filterSet:
            for objSet in filterSet.objectSet:
               task = objSet.obj
               for change in objSet.changeSet:
                  if change.name == 'info':
                     state = change.val.state
                  elif change.name == 'info.state':
                     state = change.val
                  else:
                     continue

                  if not str(task) in taskList:
                     continue

                  if state == vim.TaskInfo.State.success:
                     # Remove task from taskList
                     taskList.remove(str(task))
                  elif state == vim.TaskInfo.State.error:
                     raise task.info.error
         # Move to next version
         version = update.version
   finally:
      if filter:
         filter.Destroy()

# Start program
def main():
   """
   Simple command-line program for powering on virtual machines on a system.
   """

   args = GetArgs()
   try:
      vmnames = args.vmname
      if not len(vmnames):
         print "No virtual machine specified for poweron"
         sys.exit()

      si = None
      try:
         si = SmartConnect(host=args.host,
                           user=args.user,
                           pwd=args.password,
                           port=int(args.port))
      except IOError, e:
         pass
      if not si:
         print "Cannot connect to specified host using specified username and password"
         sys.exit()

      atexit.register(Disconnect, si)

      # Retreive the list of Virtual Machines from the invetory objects
      # under the rootFolder
      content = si.content
      objView = content.viewManager.CreateContainerView(content.rootFolder,
                                                        [vim.VirtualMachine],
                                                        True)
      vmList = objView.view
      objView.Destroy()

      # Find the vm and power it on
      tasks = [vm.PowerOn() for vm in vmList if vm.name in vmnames]

      # Wait for power on to complete
      WaitForTasks(tasks, si)

      print "Virtual Machine(s) have been powered on successfully"
   except vmodl.MethodFault, e:
      print "Caught vmodl fault : " + e.msg
   except Exception, e:
      print "Caught Exception : " + str(e)

# Start program
if __name__ == "__main__":
   main()