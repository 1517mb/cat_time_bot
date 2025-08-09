from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = "pages/about.html"


class PrivacyPolicyView(TemplateView):
    template_name = "pages/privacy_policy.html"


class TermsOfUseView(TemplateView):
    template_name = "pages/terms_of_use.html"


class PasswordGuideView(TemplateView):
    template_name = "pages/password_guide.html"


class AdminChecklistView(TemplateView):
    template_name = "pages/admin_checklist.html"


class SecurityToolsView(TemplateView):
    template_name = "pages/security_tools.html"


class FAQView(TemplateView):
    template_name = "pages/faq.html"
