from typing import Dict
from onelogin.saml2.auth import OneLogin_Saml2_Auth


class MultiIdPSAMLAuth:
    def __init__(self):
        self.idp_configs: Dict[str, dict] = {}

    def load_idp_config(self, idp_id: str, config: dict):
        """
        Load configuration for a specific IdP
        
        Args:
            idp_id: Unique identifier for the IdP
            config: SAML configuration dictionary for this IdP
        """
        self.idp_configs[idp_id] = config

    def get_auth(self, idp_id: str, request_data: dict) -> OneLogin_Saml2_Auth:
        """
        Get SAML auth instance for specific IdP
        
        Args:
            idp_id: Identifier of the IdP to use
            request_data: Request data dictionary
            
        Returns:
            OneLogin_Saml2_Auth instance configured for the specified IdP
        """
        if idp_id not in self.idp_configs:
            raise ValueError(f"No configuration found for IdP: {idp_id}")

        return OneLogin_Saml2_Auth(
            request_data,
            custom_base_path=self.idp_configs[idp_id]['custom_base_path'],
            # settings=self.idp_configs[idp_id].get('settings')
        )
