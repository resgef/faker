#!/usr/bin/env bash

sudo mkdir /var/log/faker/
sudo mkdir /var/log/faker/gunicorn/

sudo touch /var/log/faker/gunicorn/access.log
sudo touch /var/log/faker/gunicorn/error.log

sudo touch /var/log/faker/faker.log
sudo touch /var/log/faker/tropo.log

sudo chmod -R a+w /var/log/faker/