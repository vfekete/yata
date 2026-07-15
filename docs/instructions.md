# YATA - Yet Another Todo Application

# Basic functionality
 - simple todo application for GNOME / Ubuntu (primary platform)
 - gives user possibility to
     - Add task. 
     - Remove task.
     - Cancel task.
     - Mark task as done     
     - view tasks in list
 - Task is a oneliner, no special description or additional
   info.

# User interface
- Application is "bottom-most" window, basically always "laying" directly on desktop, but
  above icons
- It has no windows decorations
- It has border
- Central windows is transparent
- application is one vertical list of items
- On the right side is scrollbar which shows when necessary (eg it is not always visible)
- drag&drop allows rearranging items
- every list item represents a task
- every list item consiste out of text which is task name
- task name can be arbitrary long
- task name is wrapped based on window width
- task name supports markdown and is rendered accordingly (bold, italic, ...)
- when mouse is over a specific task on the right side 3 icons appear:
    - check, to mark the task 'done'
    - cross, to 'cancel' the task
    - re-open, to re-open the task (it is 'active', not 'done', not 'cancelled')
- by default after addition, task is in state 'active'
- both 'done' and 'cancelled' tasks are listed based on sort rules
- UI shows toolabar with actions:
   - add new task
       - creates new item on top
       - instead of text there is a placeholder 'Task name'
       - focus on item to allow setting of name
   - sort by day
       - simple list is changed to tree-like view
       - first column (top node) is date
       - leaves are tasks for given day
   - sort by status with selection of status
       - active first
       - done first
       - cancelled first
   - small input box with context search of task
      - items list is realtime changed to show results of search
      - input box contains on the right side small 'x' to cancel the search
      - input box contains place holder 'Search for task'
 - application remembers position where it was lastly moved and if closed
   it starts on the same position and resolution
      - this expects monitor order or index did not changed, if it did
        application acts as if it started for first time
      - first start puts application into the center of the current monitor
        and gives it width 20% of current monitor resolution width and
        give it aspect ration 9:16
 - application supports various themes (light / dark) with tints (blue,
   green, goldenrod, white, black)

# Development details
- Main language is python
- Main GUI framework is QtQuick and QML
- 'uv' python package manager is used for managing the python code
- always use virtual environment, never install any dependency directly

# Directory structure
- every source code is in directory 'yata-src/'
- any resources are in directory 'resources'
- any tests are in directory 'tests'
- requirements for python are in main directory
- any build scripts are in main directory
- README and BUILD docs are in main directory
- any other additional documentation is in directory 'docs/'
