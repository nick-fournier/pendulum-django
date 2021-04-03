from .models import Business

def add_context(request):
    if not request.user.is_anonymous:
        business_name = Business.objects.filter(owner__id=request.user.id).values()[0]['business_name']
        return {
            'current_business': business_name,
            'current_user': request.user
        }
    else:
        return {}
