# %%
# Importamos las librerías necesarias

import os

import dotenv
import msgraphhelper
from azure.identity import DefaultAzureCredential

dotenv.load_dotenv()

scope = "https://api.businesscentral.dynamics.com/.default"
tenant = os.environ["AZURE_TENANT_ID"]
environment = os.environ["BC_ENVIRONMENT"]
company = "ShipShop 10"


credential = DefaultAzureCredential()
session = msgraphhelper.get_graph_session(credential, scope)

api_baseurl = (
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/api/v2.0/"
)

# %%
# Buscamos el id empresa

params = {"$filter": f"name eq '{company}'"}

# Hacemos la llamada a la API
response = session.get(f"{api_baseurl}companies", params=params)
response.raise_for_status()

company_id = response.json()["value"][0]["id"]

company_baseurl = f"{api_baseurl}companies({company_id})/"

# %%
# Descargamos los datos de los clientes
response = session.get(f"{company_baseurl}customers")
response.raise_for_status()  # Si hay un error, se lanza una excepción
customers = response.json()["value"]

# %%
# Definición de paises Europeos
# fmt: off
PAISES_EUROPEOS = ["BE","BG","CZ","DK","CY","LV","LT","LU","FR","HR","IT","PL","PT","RO","SI","HU","MT","NL","AT","SK","FI","SE","DE","EE","IE","GR","IS","LI","NO","EL",] 
# fmt: on


# %%
# Definimos una función para calcular el NIF
def recalculate_tax_code(customer: dict):
    nif = customer["taxRegistrationNumber"]
    country = customer["country"]
    if country == "ES":  # Si es España, no hacemos nada
        return nif

    if country in PAISES_EUROPEOS:
        if nif[:2] in PAISES_EUROPEOS:
            return nif

        # Regla especial para Grecia
        if country == "GR":
            return f"EL{nif}"

        # Para paises europeos, añadimos el código de país al principio
        return f"{customer['country']}{nif}"

    # Para paises no europeos, añadimos el código de país al principio
    return f"{customer['country']}{customer['number']}"


# %%
# Creamos un lote
from msgraphhelper.odata import ODataBatchRequest

batch_url = f"{api_baseurl}$batch"

batch = ODataBatchRequest(
    session=session,
    batch_url=batch_url,
)

for customer in customers:
    new_nif = recalculate_tax_code(customer)
    if new_nif == customer["taxRegistrationNumber"]:
        print(
            f"Cliente {customer['displayName']} no necesita actualización. "
            f"Pais: {customer['country']} "
            f"NIF: {customer['taxRegistrationNumber']}"
        )
        continue
    batch.patch(
        id=customer["number"],
        url=f"companies({company_id})/customers({customer['id']})",  # Relativo a la URL del $batch
        headers={
            "Content-Type": "application/json",
            "If-Match": customer["@odata.etag"],
        },
        body={"taxRegistrationNumber": new_nif},
    )


# %%
# Ejecutamos el lote
batch_response = batch.send()

# %%
