# BCDayES 2024 Usar Python para desarrollar con BC

Estos son los ficheros usados para la charla de BCDayES 2024 "Usar Python para desarrollar con BC" impartida por Giles Antonio Radford el 9 de abril de 2024 en Microsoft Ibérica.

https://www.businesscentralday.es/

## Contenido

Esta carpeta contiene todo lo necesario para ejecutar el azure functions

- `presentacion.py`: El script que hemos usado en la demo
- `presentacion_simplificada.py`: la versión reducida de la demo, con menos comentarios
- `setup_company.py`: Script que ha creado las empresas de pruebas. Hace referencia a un fichero `NAV23.5.ES.ESP.STANDARD.rapidstart` que es el que se encentra en la distribución base de Microsoft.
- `COMPANY.INFO.xml`: estructura de RapidStart para el script de setup.
- `thunder-tests/`: carpeta con la configuración de Thunder Client para acceder a BC y probar las functions

## Enlaces

https://github.com/metamoof/msgraphhelper - Librería para trabajar con Microsoft Graph en Python - usado para el acceso a la API de BC
https://ngrok.com/ - utilidad para exponer un azure functions en local al internet y así poder subscribirse

# Como ejecutar Azure functions en local
