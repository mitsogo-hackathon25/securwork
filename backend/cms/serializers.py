from rest_framework import serializers

from .models import ContactSubmission, FAQItem, Page


class PageSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    meta_title = serializers.SerializerMethodField()
    meta_description = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["slug", "page_type", "title", "content", "meta_title", "meta_description", "updated_at"]

    def _lang(self):
        return self.context.get("lang", "it")

    def get_title(self, obj):
        return obj.safe_translation_getter("title", language_code=self._lang(), any_language=True)

    def get_content(self, obj):
        return obj.safe_translation_getter("content", language_code=self._lang(), any_language=True)

    def get_meta_title(self, obj):
        return obj.safe_translation_getter("meta_title", language_code=self._lang(), any_language=True)

    def get_meta_description(self, obj):
        return obj.safe_translation_getter("meta_description", language_code=self._lang(), any_language=True)


class FAQSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = FAQItem
        fields = ["id", "question", "answer", "sort_order"]

    def _lang(self):
        return self.context.get("lang", "it")

    def get_question(self, obj):
        return obj.safe_translation_getter("question", language_code=self._lang(), any_language=True)

    def get_answer(self, obj):
        return obj.safe_translation_getter("answer", language_code=self._lang(), any_language=True)


class ContactSerializer(serializers.ModelSerializer):
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "phone", "subject", "message", "website"]
