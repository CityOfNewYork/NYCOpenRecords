storage "consul" {
  address = "127.0.0.1:8500"
  path = "vault"
}

listener "tcp" {
  address = "127.0.0.1:8200"
//  tls_disable = true
  tls_cert_file = "/etc/vault.d/ssl/vault.cert"
  tls_key_file = "/etc/vault.d/ssl/vault.key"

}

cluster_name = "openrecords_vault"
