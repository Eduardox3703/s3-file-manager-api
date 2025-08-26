from dotenv import dotenv_values

# Cargar solo las variables del archivo .env sin tocar os.environ
env_vars = dotenv_values(".env")

# Mostrar las variables cargadas
print("Variables cargadas desde .env:")
for key, value in env_vars.items():
    print(f"{key} = {value}")
