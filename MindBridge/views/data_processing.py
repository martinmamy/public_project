from django.views.generic import TemplateView

class PrivacyView(TemplateView):
    template_name = "legal/privacy.html"


class TermsView(TemplateView):
    template_name = "legal/terms.html"
    
    
class PrivacyPartialView(TemplateView):
    template_name = "legal/partial/privacy_partial.html"


class TermsPartialView(TemplateView):
    template_name = "legal/partial/terms_partial.html"
    
    
class TransparentInfo(TemplateView):
    template_name = "legal/transparent_info.html"
    

class FAQView(TemplateView):
    template_name = "legal/faq.html"