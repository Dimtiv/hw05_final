from datetime import datetime


def year(request):
    year = datetime.today().year
    return {'year': year}
