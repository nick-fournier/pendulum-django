from .models import Business

def add_context(request):
    if not request.user.is_anonymous:
        # business_id = Business.objects.get(owner__id=self.request.user.id).id
        # owner_id = Owner.objects.only('owner_id').get(owner_name=owner_name).owner_id
        # owner_id = Owner.objects.values('owner_id').get(owner_name=owner_name)['owner_id']
        # owner_id = Owner.objects.values_list('owner_id', flat=True).get(owner_name=owner_name)
        query = Business.objects.filter(owner__id=request.user.id)
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
