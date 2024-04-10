# %%[markdown]
# # Demo: actualización de datos de NIF en BC
#
# Esta es la pantalla interactiva de Python para Visual Studio Code.
# Para los que los conozcáis, es similar a un libro de Jupyter,
# pero yo prefiero trabajar así... escribiendo el script en bloques
# en modo python, y dándole al botón de "Run Cell" para ejecutarlo.
#
# La pantalla a la derecha muestra lo ejecutado, y los resultados
# de la ejecución, y es una consola *REPL* (Read-Eval-Print Loop)
# que permite interactuar con los objetos en el entorno.
#
# %%
# Importamos las librerías necesarias

import os
from urllib import request

import dotenv
import msgraphhelper
from azure.identity import DefaultAzureCredential

# Cargamos las variables de entorno
dotenv.load_dotenv()

# Definiciones útiles
scope = "https://api.businesscentral.dynamics.com/.default"
tenant = os.environ["AZURE_TENANT_ID"]
environment = os.environ["BC_ENVIRONMENT"]
company = "PITONESA 06"


credential = DefaultAzureCredential()
session = msgraphhelper.get_graph_session(credential, scope)

# %%[markdown]
# # Juguemos con el API
#
# Lo primero es familiarizarnos con cómo funciona el API.
#
# El objeto `session` es un interfaz para poder hacer peticiones
# web. Se pueden hacer `get`, `post`, `patch`, `put` y `delete`.
#
# Los APIs de BC están programados con la misma filosofía que
# Microsoft Graph - es decir, utilizando el protocolo OData,
# que es una especialización del sistema REST, basado en JSON.
#
# Empecemos pidiendo un listado de objetos...

# %%
# Ejemplo 1: Listamos todas las empresas
#
# Definimos URL de la API
api_baseurl = (
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/api/v2.0/"
)

# Hacemos la llamada a la API
response = session.get(f"{api_baseurl}companies")
response.raise_for_status()  # Si hay un error, se lanza una excepción
response.json()  # Mostramos el resultado


# %%[markdown]
# # Búsquedas en el API
#
# Utilizando el parametro `$filter` añadido al final de la URL,
# podemos filtrar por cualquiera de los campos que existen en
# el JSON que devuelve el API. Hay una serie de operadores que
# se pueden usar en las expresiones, por ejemplo `eq` (de equal)
# para igual, `ne` (not equal) para no igual a, `gt` (greater than)
# para mayor que, etc. Tambien hay operadores más complejos como
# puede ser `startswith()`.


# %%
# Hacemos el filtro de que el nombre de la empresa sea el que hemos
# definido arriba. Atención que las cadenas van en comillas simples.
params = {"$filter": f"name eq '{company}'"}

# Hacemos la llamada a la API
response = session.get(f"{api_baseurl}companies", params=params)
response.raise_for_status()  # Si hay un error, se lanza una excepción
response.json()  # Mostramos el resultado

# %%[markdown]
#
# # Llamando a instancias de un objeto en OData
#
# OData permite llamar a objetos específicos poniendo la clave primeria en paréntesis.
#
# En el caso de Web Services de Business Central la clave principal normalmente es el Código
# asociado con el objeto, el mismo que declaras como `key(PK; FieldName)` en AL. Se permiten
# claves de multiples campos. Esto se puede ver analizando el documento Metadatos que
# puedes consultar llamando al endoint de `$metadata`.
#
# En el caso del api standard de Microsoft, optaron por utilizar el campo `id`, que
# equivale al campo `SystemId` en AL. Esto lo han hecho por mayor compatibilidad con
# PowerPlatform, pero no para de ser un engorro, porque requiere buscar el `SystemId` de
# todos los objetos relacionados.
# %%
# Guardamos el ID de la empresa
company_id = response.json()["value"][0]["id"]

# Aprovechamos para crear una URL base para la empresa
company_baseurl = f"{api_baseurl}companies({company_id})/"

company_baseurl

# %%
response = session.get(url=company_baseurl)
response.raise_for_status()
response.json()

# %%[markdown]
# # JSON de un objeto
#
# A diferencia del listado de objetos, en el que el resultado va en una lista que se llama
# `value` dentro del objeto raíz, aquí el objeto raíz es la repesentación del objeto OData
# directamente.

# %%[markdown]
# # Descargamos los datos de los clientes
#
# Esto lo hacemos pidiendo los `customers` de la instancia de `companies`
# %%
# Descargamos los datos de los clientes
response = session.get(f"{company_baseurl}customers")
response.raise_for_status()  # Si hay un error, se lanza una excepción
customers = response.json()["value"]
customers

# %%[markdown]
# # Actualización de un cliente
#
# Los objetos de OData se actualizan enviando una petición `PATCH` a la URL del objeto a
# actualizar. Como regla general, se debe de hacer una petición `PATCH` por objeto.
#
# Para evitar el machaque de datos incorrecto, cada vez que se descarga un objeto, verás
# que hay una entrada de `@odata.etag` - esto es un indicador del estado actual de la BBDD
# de BC. Al actualizar el objeto hay que enviar una cabecera de `If-Match` con el contenido
# de ese etag. Si no se incluye, dará un error. Si no coincide, entonces dará un error.

# %%
# Probamos con un cliente
customer = customers[0]
customer
# %%
# Intentamos actualizar el NIF del cliente sin pasar cabecera `If-Match`
response = session.patch(
    f"{company_baseurl}customers({customer['id']})",
    json={"taxRegistrationNumber": "ES12345678A"},
    headers={
        "Content-Type": "application/json",
    },
)
response.raise_for_status()
response.json()

# %%
# Intentamos actualizarlo con la cabecera `If-Match`
response = session.patch(
    f"{company_baseurl}customers({customer['id']})",
    json={"taxRegistrationNumber": "A123456789"},
    headers={
        "Content-Type": "application/json",
        "If-Match": customer["@odata.etag"],
    },
)
response.raise_for_status()
saved_response = response.json()  # lo guardamos para luego
response.json()

# %%
# volvemos a intentar la misma operación con otro NIF
response = session.patch(
    f"{company_baseurl}customers({customer['id']})",
    json={"taxRegistrationNumber": "B987654321"},
    headers={
        "Content-Type": "application/json",
        "If-Match": customer["@odata.etag"],
    },
)
response.raise_for_status()
response.json()

# %%
# volvemos a intentalo con el etag que guardamos de la operación exitosa
response = session.patch(
    f"{company_baseurl}customers({saved_response['id']})",
    json={"taxRegistrationNumber": "B987654321"},
    headers={
        "Content-Type": "application/json",
        "If-Match": saved_response["@odata.etag"],
    },
)
response.raise_for_status()
response.json()

# %%[markdown]
# # Saltandose el control del etag
#
# En algunos casos puede ser deseable saltarse este mecanismo anti-machaque.
# Si fuera necesario, se puede especificar `If-Match: *` y entonces se saltará el
# control
#
# **No es recomendable hacerlo en un script de producción**

# %%
# Mismo ejemplo que arriba, volviendo a cambiar el nif, pero sin el etag.
response = session.patch(
    f"{company_baseurl}customers({saved_response['id']})",
    json={"taxRegistrationNumber": "C6666666666"},
    headers={
        "Content-Type": "application/json",
        "If-Match": "*",
    },
)
response.raise_for_status()
response.json()

# %%[markdown]
# # Paso 3: Actualizamos los datos de los clientes en masa
#
# Recapitulando:
# - NIF Español: no se cambia
# - NIF Comunitario: Incluye el país de origen al principio
# - NIF Extranjero: El País más el código de cliente


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
# Montamos un bucle para actualizar los clientes
# de momento lo limitamos a 10.
for customer in customers[1:11]:
    new_nif = recalculate_tax_code(customer)
    if new_nif == customer["taxRegistrationNumber"]:
        print(
            f"Cliente {customer['displayName']} no necesita actualización. "
            f"Pais: {customer['country']} "
            f"NIF: {customer['taxRegistrationNumber']}"
        )
        continue
    response = session.patch(
        f"{company_baseurl}customers({customer['id']})",
        json={"taxRegistrationNumber": new_nif},
        headers={
            "Content-Type": "application/json",
            "If-Match": customer["@odata.etag"],
        },
    )
    response.raise_for_status()
    print(
        f"Cliente {customer['displayName']} actualizado. "
        f"Pais: {customer['country']} "
        f"Nuevo NIF: {new_nif}"
    )
# %%[markdown]
# # Uso de lote para actualizar los clientes
#
# En lugar de actualizar los clientes uno a uno, podemos usar un lote para actualizar
# varios clientes a la vez. A nivel API, esto se traduce en una única llamada a la API
# con varias peticiones. Se pueden meter hasta 100 peticiones en un lote.
#
# El formato de lote no es complicado:
#
# ```json
# {
#     "requests": [
#         {
#             "id": "id de la operacion",
#             "method": "PATCH",
#             "headers": {
#                 "If-Match": "W\"123453234543234542335\""
#                 },
#             "body": {
#                 "taxRegistrationNumber": "loquesea"
#                 },
#         }
#     ]
# }
# ```
#
# Pero es más fácil usar una librería que nos ayude a montar el lote.
# En este caso, introduzco `msgraphhelper.odata.ODataBatchRequest`
#

# %%
# Importamos la librería necesaria
from msgraphhelper.odata import ODataBatchRequest, ODataBatchResponse

# La URL del endpoint de batch es el siguiente:
batch_url = f"{api_baseurl}$batch"
# https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/api/v2.0/$batch

# Creamos un lote
batch = ODataBatchRequest(
    session=session,
    batch_url=batch_url,
    ## Estas variables son opcionales, las dejo para comentar
    max_batch_size=100,  # Esto es el máximo de peticiones que se pueden meter en un lote
    continue_on_error=True,  # Si hay un error, se ejecutan con las siguientes peticiones
    isolation_snapshot=True,  # Crea una especia de Transaccion en la BBDD
)

# Recreamos el bucle anterior, pero en lugar de hacer un PATCH, añadimos la petición al lote
for customer in customers[11:]:
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

len(batch)
# %%
# Ejecutamos el lote
batch_response = batch.send()
# Esto devuelve un objeto de tipo ODataBatchResponse
# que es un dict contiene las respuestas de cada petición,
# con el id de la petición como clave

batch_response[list(batch_response.keys())[0]]  # type: ignore
# %%
# Paso final - abrimos la web de BC para comprobar los cambios
import webbrowser

webbrowser.open(
    f"https://businesscentral.dynamics.com/{tenant}/{environment}/?company={company_id}&page=22"
)
