# NYC.ID Authentication Setup

The NYC OpenRecords application is required to utilize SAML for authentication as per DoITT requirements. There are a number of setup steps that need to occur before SAML can be setup to work from a developer workstation.

## External IP for Vagrant
In order to communicate with NYC.ID, your Vagrant machine must be accessible on CityNet. In order to do this you need to add the following line to the Vagrant configuration for your `Default` VM.

```ruby
    default.vm.network "public_network", ip: "10.132.32.XXX", bridge: "en0: Ethernet"
```

This sets up a Bridged-Network on your Vagrant machine allowing you to have a Citynet IP address. DORIS has reserved IPs 10.132.32.200 thru 10.132.32.250 for the development team.

Use NMAP to find a host that is not in use and set your VM IP to that host. 

**Note;** We are working on a better way to manage available IPs on our network.

You will also need to modify your Nginx configuration to listen on this IP address.

```
server_name     10.132.32.XXX;

```

## Domain Name for Vagrant
You will need to create an A-Record in the `appdev.records.nycnet` domain that points to the IP address you selected above.

If you do not have access to the DNS server, please contact Joel Castillo or Ho Yin (Kenneth) Chan on Slack, and they will assist you.

The recommended naming convention for your URL is: `project-environment-dev_name`. 

Where:
- Project = Project Name (e.g. OpenRecords)  
- Environment = DEV, TST, STG, PRD  
- Dev_Name = Your first name  

Ex:   
`openrecords-dev-joel.appdev.records.nycnet`

Once the A-Record has been created, you will need to modify your Nginx server_name configuration to accept requests from this domain as well.

Example: 
```
server_name                         openrecords-dev-joel.appdev.records.nycnet;
```
## Setup you NYC.ID Service Account
1. Login to the NYC.ID Console
2. Create a new service account.  
Your should fill out the fields in the following way:
   ```markdown
   Display Name: Project Name (Environment) - Developer First Name
   Name: <project_name>_<environment>_<developer_first_name>
   URL: <URL created above. e.g. openrecords-dev-joel.appdev.records.nycnet
   Email Address: your_email@records.nyc.gov
   ```
3. Store your service account name in your .env (`SAML_NYC_ID_USERNAME`)
4. Store you servie account password in your .env (`SAML_NYC_ID_PASSWORD`)


# Create Self-Signed Certs
1. Create self-signed certs using the command:
 ```markdown
 openssl req -new -x509 -days 3652 -nodes -out saml.crt -keyout saml.key
 ```

# Setup your NYC.ID Service Provider
1. Login to the NYC.ID Console
2. Create a new SAML Service Provider
   ```markdown
   Service Provicer: <Choose the Service Provider created in Step 2
   Assertion Consumer Service URL: <URL created above>/auth/saml?acs
   Single Logout Service URL: <URL created above>/auth/saml?sls
   Name: <URL created above>
   Issuer: <URL created above>/auth/metadata
   Single Logout Service Binding: `urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect`
   X.509 Certificate: Copy the contents of `/vagrant/instance/saml/certs/saml.crt`
   Encrypt Assertions: False (unchecked)
   X.509 Encryption Certificate: Copy the contents of `/vagrant/instance/saml/certs/saml.crt`
   ```

## Setup SAML Configuration
DORIS uses a lightly customized [OneLogin python3-saml](https://github.com/onelogin/python3-saml) package embedded in our codebase. It looks for configuration in the `/vagrant/instance/saml` directory by default. This can be changed by editing the corresponding environment variable in `.env`

1. `cp /vagrant/instance/saml/settings.json.example /vagrant/instance/saml/settings.json`
2. `cp  /vagrant/instance/saml/advanced_settings.json.example /vagrant/instance/saml/advanced_settings.json`

### Edit `/vagrant/instance/saml/settings.json`
1. Copy the contents of `/vagrant/instance/saml/certs/saml.key` into `sp['privateKey']`  
   Note: You may need to open the file in another editor and remove all linebreaks.
2. Copy the contents of `/vagrant/instance/saml/certs/saml.cert` into `sp['x509cert']`  
   Note: You may need to open the file in another editor and remove all linebreaks.
3. Replace all occurrences of `<sp_domain>` with the URL you added to the DNS server earlier.
4. Open the IdP metadata and copy the `x509cert` from the metadata into `idp[x509cert]`.  
The IdP Metadata can be found by visiting the [NYC4D Authentication Documentation](http://nyc4d-stg.nycnet/nycid/authentication.shtml#idp-install). 
5. Replace `<idp_slo_url>` with the corresponding value from the IdP metadata.
6. Replace `<idp_sso_url>` with the corresponding value from the IdP metadata

### Edit `/vagrant/instance/saml/advanced_settings.json`
1. Update the contact person with your information (email address and name)
2. Update the organization with the URL you created before and a unique name and display name.


If you have questions about the specific implementation that DoITT provides, please visit [NYC4D NYC.ID 2.0](http://nyc4d-stg.nycnet/).