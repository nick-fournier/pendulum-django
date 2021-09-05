from .models import Business

def add_context(request):
    if not request.user.is_anonymous:
        query = Business.objects.filter(business_user__id=request.user.id)
        if query:
            business_name = query.first()
        else:
            business_name = None

        return {
            'current_business': business_name,
            'current_user': request.user
        }
    else:
        return {}
