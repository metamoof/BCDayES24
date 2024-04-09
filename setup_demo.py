# %%
import json
import logging
import os
import random
import time
from pathlib import Path

import dotenv
from azure.identity import DefaultAzureCredential

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

dotenv.load_dotenv()


import msgraphhelper.odata
from msgraphhelper.session import get_graph_session

bc_scope = "https://api.businesscentral.dynamics.com/.default"
baseurl = f"https://api.businesscentral.dynamics.com/v2.0/{os.environ['AZURE_TENANT_ID']}/{os.environ['BC_ENVIRONMENT']}/"

credentials = DefaultAzureCredential()
bc_session = get_graph_session(credentials, bc_scope)


# %%

# automation api
automation_url = baseurl + "api/microsoft/automation/v2.0/"

# get comapanies
response = bc_session.get(automation_url + "companies")
companies = response.json()["value"]

# %%
first_company_id = companies[0]["id"]

companies = [c["name"] for c in companies if c["name"].startswith("PITONESA")]

if companies:
    latest = max(companies)
    count = int(latest.split(" ")[1])
    company_display_name = f"Pitonesa Prodigiosa {count + 1}"
    company_name = f"PITONESA {count + 1:02d}"
else:
    company_display_name = "Pitonesa Prodigiosa 1"
    company_name = "PITONESA 01"
    count = 0

logging.info(f"Creando nueva empresa: {company_display_name}")

# create a new ShipShop company
response = bc_session.post(
    automation_url + f"companies({first_company_id})/automationCompanies",
    json={
        "displayName": company_name,
        "name": company_name,
    },
)
company_info = response.json()
company_id = company_info["id"]
company_name = company_info["name"]
# company_display_name = company_info["displayName"]
logging.info(
    f"Empresa creada: Id: {company_info['id']} Nombre: {company_info['name']} Nombre visible: {company_info['displayName']}"
)
# %%
response = bc_session.patch(
    automation_url + f"companies({first_company_id})/automationCompanies({company_id})",
    json={
        "displayName": company_display_name,
    },
    headers={"If-Match": company_info["@odata.etag"]},
)
response.raise_for_status()
response.json()

# %%

PACKAGE_CHECK_SLEEP_TIME = 5  # segundos


def load_rapidstart(bc_session, company_id: str, package_name: str, data: bytes):
    company_automation_url = automation_url + f"companies({company_id})/"

    # Creamos un nuevo paquete de configuración para la configuración básica de BC
    response = bc_session.post(
        company_automation_url + "configurationPackages",
        json={"code": package_name},
    )
    package_info = response.json()
    package_id = package_info["id"]
    logging.info(
        f"Paquete de configuración creado: Id: {package_info['id']} Nombre: {package_info['code']}"
    )

    # Cargamos el paquete de configuración
    conf_file_url = (
        company_automation_url
        + f"configurationPackages({package_id})/file('{package_info['code']}')"
    )
    response = bc_session.get(conf_file_url)
    file_info = response.json()

    response = bc_session.patch(
        company_automation_url
        + f"configurationPackages({package_id})/file('{package_info['code']}')/content",
        headers={
            "Content-Type": "application/octet-stream",
            "If-Match": file_info["@odata.etag"],
        },
        data=data,
    )
    response.raise_for_status()
    logging.info("Paquete de configuración cargado")

    # Importamos el paquete de configuración
    response = bc_session.post(
        company_automation_url
        + f"configurationPackages({package_id})/Microsoft.NAV.import",
    )
    response.raise_for_status()
    logging.info(
        f"Importación de paquete de configuración {package_info['code']} solicitada"
    )

    # Revisamos el estado de la importación
    while True:
        time.sleep(PACKAGE_CHECK_SLEEP_TIME)
        response = bc_session.get(
            company_automation_url + f"configurationPackages({package_id})"
        )
        package_info = response.json()
        logging.info(
            f"Estado del paquete de configuración {package_info['code']}: {package_info['importStatus']}"
        )
        if package_info["importStatus"] not in ("Scheduled", "InProgress"):
            break
    logging.info(
        f"Importación de paquete de configuración {package_info['code']} completada"
    )

    # Aplicamos el paquete de configuración
    response = bc_session.post(
        company_automation_url
        + f"configurationPackages({package_id})/Microsoft.NAV.apply",
    )
    response.raise_for_status()
    logging.info(
        f"Aplicación del paquete de configuración {package_info['code']} solicitada"
    )

    # Revisamos el estado de la aplicación
    while True:
        time.sleep(PACKAGE_CHECK_SLEEP_TIME)
        response = bc_session.get(
            company_automation_url + f"configurationPackages({package_id})"
        )
        package_info = response.json()
        logging.info(
            f"Estado del paquete de configuración {package_info['code']}: {package_info['applyStatus']}"
        )
        if package_info["applyStatus"] not in ("Scheduled", "InProgress"):
            break
    logging.info(
        f"Aplicación de paquete de configuración {package_info['code']} completada"
    )


# %%
# Cargamos el paquete de configuración genérico de BC
load_rapidstart(
    bc_session=bc_session,
    company_id=company_id,
    package_name="ES.ESP.STANDARD",
    data=Path("NAV23.5.ES.ESP.STANDARD.rapidstart").read_bytes(),
)

# %%
# Creamos el paquete de configuración de empresa base
company_config = Path("COMPANY.INFO.xml").read_text(encoding="utf-16")
company_shortcode = f"Py {count+1}"
company_upper_code = company_id.upper()
company_config = company_config.format(
    company_name=company_name,
    company_display_name=company_display_name,
    company_shortcode=company_shortcode,
    company_upper_code=company_upper_code,
)

import gzip

company_config_gz = gzip.compress(company_config.encode("utf-16"))

Path(f"COMPANY.INFO.{company_shortcode}.xml").write_text(company_config)
Path(f"COMPANY.INFO.{company_shortcode}.rapidstart").write_bytes(company_config_gz)

load_rapidstart(
    bc_session=bc_session,
    company_id=company_id,
    package_name="COMPANY.INFO." + company_shortcode,
    data=company_config_gz,
)


# %%

from faker import Faker

faker_locales = [
    "az_AZ",
    "bn_BD",
    "cs_CZ",
    "en_US",
    "en_GB",
    "es_ES",
    "da_DK",
    "de_AT",
    "de_CH",
    "de_DE",
    "el_GR",
    "en_AU",
    "en_BD",
    "en_CA",
    "en_GB",
    "en_IE",
    "en_IN",
    "en_NZ",
    "en_PH",
    "es_AR",
    "es_ES",
    "es_CL",
    "es_CO",
    "es_MX",
    "fa_IR",
    "fi_FI",
    "fil_PH",
    "fr_BE",
    "fr_CA",
    "fr_CH",
    "fr_FR",
    "hr_HR",
    "hu_HU",
    "hy_AM",
    "id_ID",
    "it_CH",
    "it_IT",
    "ja_JP",
    "ka_GE",
    "ko_KR",
    "nl_BE",
    "nl_NL",
    "no_NO",
    "pl_PL",
    "pt_BR",
    "ro_RO",
    "ru_RU",
    "sk_SK",
    "sl_SI",
    "sv_SE",
    "th_TH",
    "tl_PH",
    "uk_UA",
    "zh_CN",
    "zh_TW",
]
fake = Faker(faker_locales)
# %%

api_url = baseurl + f"api/v2.0/companies({company_id})/"

# Buscamos los ids de los grupos de IVA de compras y ventas
response = bc_session.get(api_url + "taxAreas")
response.raise_for_status()
tax_areas = {v["code"]: v["id"] for v in response.json()["value"]}

# Creamos clientes de ejemplo


customer_request_template = {
    "displayName": "company",
    "type": "@Person",
    "addressLine1": "street_address",
    "city": "city",
    # "state": "state",
    "country": "current_country_code",
    "postalCode": "postcode",
    # "phoneNumber": "phone_number",
    "email": "email",
    "website": "url",
    "taxRegistrationNumber": "ssn",
    "blocked": "@ ",
}

EEA_COUNTRIES = [
    "BE",
    "BG",
    "CZ",
    "DK",
    "CY",
    "LV",
    "LT",
    "LU",
    "FR",
    "HR",
    "IT",
    "PL",
    "PT",
    "RO",
    "SI",
    "HU",
    "MT",
    "NL",
    "AT",
    "SK",
    "FI",
    "SE",
    "DE",
    "EE",
    "IE",
    "GR",
    "IS",
    "LI",
    "NO",
    "EL",
]

# %%
batch_request = msgraphhelper.odata.ODataBatchRequest(
    session=bc_session, batch_url=baseurl + f"api/v2.0/$batch"
)

for x in range(600):
    locale = random.choice(fake.locales)
    customer_data = fake[locale].json(
        data_columns=customer_request_template, num_rows=1
    )
    customer_data = json.loads(customer_data)

    if customer_data["country"] == "ES":
        customer_data["taxAreaId"] = tax_areas["NAC"]
    elif customer_data["country"] in EEA_COUNTRIES:
        customer_data["taxAreaId"] = tax_areas["UE"]
    else:
        customer_data["taxAreaId"] = tax_areas["EXPORT."]
        customer_data["taxRegistrationNumber"] = ""

    batch_request.post(
        id=f"post_customer_{x}",
        url=f"companies({company_id})/customers",
        body=customer_data,
    )

# %%

response = batch_request.send()

# %%
import webbrowser

webbrowser.open(
    f"https://businesscentral.dynamics.com/{os.environ['AZURE_TENANT_ID']}/{os.environ['BC_ENVIRONMENT']}/?company={company_name}"
)

# %%
