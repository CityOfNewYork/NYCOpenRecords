<img src="https://www1.nyc.gov/assets/records/images/content/header/logo.png" alt="NYC Department of Records and Information Services" width="200px" /><img src="https://a860-openrecords.nyc.gov/static/img/logo.png" alt="NYC OpenRecords" width="200px" />  
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/2b97fe8319344d699a4bbba48827637b)](https://www.codacy.com/app/NYCRecords/NYCOpenRecords?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=CityOfNewYork/NYCOpenRecords&amp;utm_campaign=Badge_Grade)

# NYC OpenRecords
NYC OpenRecords is an application that assists individuals in the process of submitting Freedom of Information Law (FOIL) requests to a NYC Agency. The web application also allows government employees to manage, respond to, and fulfill incoming requests.

## Getting Started

### Technical Requirements
OpenRecords is currently being developed on RedHat Enterprise Linux v6 / v7 (in testing). 

It relies on the following technologies:
- Python v3.5 
- PostgreSQL v9.5
- ElasticSearch v5.2
- Redis v3.2

Authentication 
- OpenRecords currently implements LDAP and OAuth for authentication. For development, you can bypass authentication by setting both `'USE_OAUTH'` and `'USE_LDAP'` to `False`.
    
We have optional integrations with [Sentry](https://sentry.io) for error tracing and are working on an integration with the ELK stack for log aggregation and analytics.

### Pre-Requisites
- Vagrant (v2.1.4) - Newer version may work but have not been tested.
- Virtualbox (v5.1.32) - Newer versions may work but have not been tested.
- [Vagrant-VBGuest](https://github.com/dotless-de/vagrant-vbguest)
- Redhat Developer Account (https://developers.redhat.com)
- FakeSMTP (Optional, for testing email functionality)

### Setting Up Development Environment (WIP)

#### On Mac OS X:
1. Install Virtualbox and Vagrant.
2. Install vagrant-vbguest:
    ```bash
    vagrant plugin install vagrant-vbguest
    ```
3. Create your `.env` file:
    ```bash
    cp .env.example .env
    ```
4. Edit your `.env` file. Look at the comments in `.env.example` and `config.py` for examples of valid values.
5. Create your `Vagrantfile`
    ```bash
    cp Vagrantfile.example Vagrantfile
    ```
5. Startup your Vagrant machine 
    ```bash
    RH_USER=<YOUR REDHAT DEVELOPER USERNAME> RH_PASS=<YOUR REDHAT DEVELOPER PASSWORD> vagrant up default
    
    ```
6. Once Vagrant has finished setting up the VM, ssh in to the system (`vagrant ssh`). You'll need to have 2 different SSH Sessions open.
    Terminal 1 - Celery
    ```bash
    sh /vagrant/.startup/celery_startup.sh
    ```
    Terminal 2 - Flask
    ```bash
    sh /vagrant/.startup/flask_startup.sh
    ```
    
#### On Windows:
**TBD** (If you would like to help us setup a development environment on Windows, please try it out and submit issues as they come up.)
    
## Questions?
Please open an issue in this repository if you have any questions or any difficulty setting up and using OpenRecords.
