from rest_framework import serializers
from .models import Exam, Question, Choice, ExamAttempt, Answer
from courses.serializers import CourseSerializer

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id', 'choice_text', 'is_correct')

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'question_type', 'marks', 'order', 'choices')

class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    
    class Meta:
        model = Question
        fields = ('question_text', 'question_type', 'marks', 'order', 'choices')
    
    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        # Update the question fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            # Remove choices not present in the update
            existing_ids = [c.get('id') for c in choices_data if c.get('id')]
            for choice in instance.choices.all():
                if choice.id not in existing_ids:
                    choice.delete()

            # Update or create choices
            for choice_data in choices_data:
                choice_id = choice_data.get('id', None)
                if choice_id:
                    # Update existing choice
                    choice = Choice.objects.get(id=choice_id, question=instance)
                    choice.choice_text = choice_data.get('choice_text', choice.choice_text)
                    choice.is_correct = choice_data.get('is_correct', choice.is_correct)
                    choice.save()
                else:
                    # Create new choice
                    Choice.objects.create(question=instance, **choice_data)
        return instance

class ExamSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exam
        fields = '__all__'

class ExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ('title', 'description', 'duration', 'total_marks', 'passing_marks',
                 'start_time', 'end_time', 'is_published', 'course')

class StaffExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ('title', 'description', 'duration', 'total_marks', 'passing_marks',
                 'start_time', 'end_time', 'is_published')

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ('question', 'answer_text')

class ExamAttemptSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(read_only=True)
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = ExamAttempt
        fields = ('id', 'exam', 'student', 'start_time', 'end_time', 'score',
                 'is_completed', 'answers')
        read_only_fields = ('student', 'score', 'is_completed')

class ExamSubmissionSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)
    
    def validate(self, data):
        attempt = self.context['attempt']
        exam = attempt.exam
        
        # Validate that all questions are answered
        answered_questions = set(answer['question'].id for answer in data['answers'])
        exam_questions = set(question.id for question in exam.questions.all())
        
        if answered_questions != exam_questions:
            raise serializers.ValidationError("All questions must be answered.")
        
        return data