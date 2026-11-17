#!/usr/bin/env bash

flask db upgrade

exec "$@"
