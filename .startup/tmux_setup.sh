#!/bin/zsh
session_name=openrecords
window_one=vagrant
window_two=development

# Reset Session
tmux kill-session -t $session_name

# Window 1 Layout - Three horizontally spaced panes
#
# ----------------------------------
# |          |          |          |
# |  CELERY  |   FLASK  |   SMTP   |
# |          |          |          |
# ----------------------------------
tmux new-session -d -s $session_name -n $window_one
tmux split-window -d -t $session_name:$window_one.1 -h
tmux split-window -d -t $session_name:$window_one.1 -h
tmux send-keys -t $session_name:$window_one.1 'vagrant ssh -- -t "sh /vagrant/.tmux/celery_startup.sh"' C-m 
tmux send-keys -t $session_name:$window_one.2 'vagrant ssh -- -t "sh /vagrant/.tmux/flask_startup.sh"' C-m 
tmux send-keys -t $session_name:$window_one.3 'vagrant ssh -- -t "sh /vagrant/.tmux/fakesmtp_startup.sh"' C-m 

# Window 2 Setup - 2 horizontally spaced panes
#
# ----------------------------------
# |                |               |
# |     VAGRANT    |     LOCAL     |
# |                |               |
# ----------------------------------
tmux new-window -d -t $session_name -n $window_two
tmux split-window -d -t $session_name:$window_two.1 -h
tmux select-layout -t $session_name:$window_two even-horizontal
tmux send-keys -t $session_name:$window_two.1 'vagrant ssh' C-m

# Attach to tmux session
tmux a -dt $session_name