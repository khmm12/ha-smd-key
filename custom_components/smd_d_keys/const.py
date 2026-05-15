"""Constants for SMD D-KEYS."""

from __future__ import annotations

DOMAIN = "smd_d_keys"
NAME = "SMD D-KEYS"

CONF_ACCOUNT_ID = "account_id"
CONF_CMDC_URL = "cmdc_url"
CONF_L2_URL = "l2_url"
CONF_OTP = "otp"
CONF_PHONE = "phone"
CONF_RELOCK_DELAY = "relock_delay"
CONF_SELECTED_DOORS = "selected_doors"
CONF_TOKEN = "token"

DEFAULT_RELOCK_DELAY = 5

DEFAULT_MDE_URL = "https://mde.s-m-d.ru:38257/DKeys_app_3/MAIN.php/"
DEFAULT_CMDC_URL = "https://cmdc.s-m-d.ru:8626"
DEFAULT_L2_URL = "http://mqapp.s-m-d.ru:47393"

APP_OS = "Android"
APP_LANG = "ru"
APP_VERSION = "5.3.10"
APP_VERSION_OS = "15"
