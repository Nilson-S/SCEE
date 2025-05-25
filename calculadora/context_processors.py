from datetime import datetime

def fecha_actual(request):
    return {
        'now': datetime.now()
    }
