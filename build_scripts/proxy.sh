#!/usr/bin/env bash
#      ______ ______  ________  ____    __
#     / __  // __  / / __  /\ \/ /\ \  / /
#    / /_/ // /_/ / / / / /  \  /  \ \/ /
#   / ____//   __/ / / / /   /  \   \  /
#  / /    / /\ \  / /_/ /   / /\ \  / /
# /_/    /_/  \_\/_____/   /_/  \_\/_/.sh
#

function set_proxy() {
	git config --global http.proxy http://bcpxy.nycnet:8080
	export http_proxy=http://bcpxy.nycnet:8080
	export https_proxy=http://bcpxy.nycnet:8080
	export no_proxy=localhost,127.0.0.0/8,127.0.1.1,127.0.1.1*

	sudo subscription-manager config --server.proxy_hostname=bcpxy.nycnet --server.proxy_port=8080
}

function unset_proxy() {
	git config --global --unset-all http.proxy
	unset http_proxy
	unset https_proxy
	unset no_proxy
	sudo subscription-manager config --server.proxy_hostname= --server.proxy_port=
}

# Set automatically.
set_proxy
