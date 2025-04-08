class NoCacheMiddleware:
    """
    Middleware para desactivar el caching.
    Establece las cabeceras 'Cache-Control', 'Pragma' y 'Expires' en cada respuesta.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response