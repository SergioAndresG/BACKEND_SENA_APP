import string
import random
import secrets


# Función para generar una contraseña segura
def generar_contraseña():
    #Longitud de la contraseña
    longitud_comtraseña = 8

    # Caracteres especiales
    cacaracteres_especiales = ".-&#_"

    #Caracteres que se van a usuar para generar la contraseña
    cacaracteres = string.ascii_letters + string.digits + cacaracteres_especiales

    #lista para guardar las contraseñas generadas
    contraseñas_generadas = []

    contraseñas_generadas.append(random.choice(string.ascii_uppercase)) # Al menos una letra mayúscula
    contraseñas_generadas.append(random.choice(string.ascii_lowercase)) # Al menos una letra
    contraseñas_generadas.append(random.choice(string.digits)) # Al menos un dígito
    contraseñas_generadas.append(random.choice(cacaracteres_especiales)) # Al menos un caracter especial
    
    # Mientras la contraseña que generda sea menor a la longitus se va a ir generando un caracter aleatorio
    while len(contraseñas_generadas) < longitud_comtraseña:
        # Se pega en el array de la contraseña a generar un caracter aleatorio
        contraseñas_generadas.append(secrets.choice(cacaracteres))
    # Mezclamos de manera aleatoria los caracteres para evitar patrones
    random.shuffle(contraseñas_generadas)

    # Convertimos lka contraseña auna cadena de caracteres
    contraseñas_generadas = ''.join(contraseñas_generadas)

    # Retornam,os la contraseña generada
    return contraseñas_generadas
