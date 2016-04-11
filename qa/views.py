import operator
from functools import reduce
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.views.generic import CreateView, View, ListView, DetailView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from qa.models import (UserQAProfile, Question, Answer, AnswerVote,
                       QuestionVote, AnswerComment, QuestionComment)
from .mixins import LoginRequired

'''
Dear maintainer:

Once you are done trying to 'optimize' this routine, and have realized what a
terrible mistake that was, please increment the following counter as a warning
to the next guy:

total_hours_wasted_here = 2
'''


class QuestionIndexView(ListView):
    '''CBV to render the index view
    '''
    model = Question
    paginate_by = 10
    context_object_name = 'questions'
    template_name = 'qa/index.html'

    def get_context_data(self, *args, **kwargs):
        context = super(
            QuestionIndexView, self).get_context_data(*args, **kwargs)
        context['totalcount'] = Question.objects.count
        context['anscount'] = Answer.objects.count
        context['noans'] = Question.objects.order_by('-pub_date').filter(
            answer__isnull=True)[:10]
        context['reward'] = Question.objects.order_by('-reward').filter(
            answer__isnull=True, reward__gte=1)[:10]
        return context


class QuestionsSearchView(QuestionIndexView):
    """
    Display a ListView page inherithed from the QuestionIndexView filtered by
    the search query and sorted by the different elements aggregated.
    """

    def get_queryset(self):
        result = super(QuestionsSearchView, self).get_queryset()
        query = self.request.GET.get('word')
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_,
                       (Q(title__icontains=q) for q in query_list)) |
                reduce(operator.and_,
                       (Q(description__icontains=q) for q in query_list))
            )

        return result

        def get_context_data(self, *args, **kwargs):
            context = super(
                QuestionsSearchView, self).get_context_data(*args, **kwargs)
            context['totalcount'] = Question.objects.count
            context['anscount'] = Answer.objects.count
            context['noans'] = Question.objects.order_by('-pub_date').filter(
                answer__isnull=True)[:10]
            context['reward'] = Question.objects.order_by('-reward').filter(
                answer__isnull=True, reward__gte=1)[:10]
            return context


class QuestionsByTagView(ListView):
    '''View to call all the questions clasiffied under one specific tag.
    '''
    model = Question
    paginate_by = 10
    context_object_name = 'questions'
    template_name = 'qa/index.html'

    def get_queryset(self, **kwargs):
        return Question.objects.filter(tags__name__contains=self.kwargs['tag'])

    def get_context_data(self, *args, **kwargs):
        context = super(
            QuestionsByTagView, self).get_context_data(*args, **kwargs)
        context['totalcount'] = Question.objects.count
        context['anscount'] = Answer.objects.count
        context['noans'] = Question.objects.order_by('-pub_date').filter(
            tags__name__contains=self.kwargs['tag'], answer__isnull=True)[:10]
        context['reward'] = Question.objects.order_by('-reward').filter(
            tags__name__contains=self.kwargs['tag'], answer__isnull=True,
            reward__gte=1)[:10]
        return context


class CreateQuestionView(LoginRequired, CreateView):
    """
    View to handle the creation of a new question
    """
    template_name = 'qa/create_question.html'
    model = Question
    fields = ['title', 'description', 'tags']

    def form_valid(self, form):
        """
        Create the required relation
        """
        form.instance.user = self.request.user
        return super(CreateQuestionView, self).form_valid(form)

    def get_success_url(self):
        return reverse('qa_index')


class CreateAnswerView(LoginRequired, CreateView):
    """
    View to create new answers for a given question
    """
    template_name = 'qa/create_answer.html'
    model = Answer
    fields = ['answer_text']

    def form_valid(self, form):
        """
        Creates the required relationship between answer
        and user/question
        """
        form.instance.user = self.request.user
        form.instance.question_id = self.kwargs['question_id']
        return super(CreateAnswerView, self).form_valid(form)

    def get_success_url(self):
        return reverse('qa_detail', kwargs={'pk': self.kwargs['question_id']})


class UpdateAnswerView(LoginRequired, UpdateView):
    """
    Updates the question
    """
    template_name = 'qa/update_answer.html'
    model = Answer
    pk_url_kwarg = 'answer_id'
    fields = ['answer_text']

    def get_success_url(self):
        answer = self.get_object()
        return reverse('qa_detail', kwargs={'pk': answer.question.pk})


class CreateAnswerCommentView(LoginRequired, CreateView):
    """
    View to create new comments for a given answer
    """
    template_name = 'qa/create_comment.html'
    model = AnswerComment
    fields = ['comment_text']

    def form_valid(self, form):
        """
        Creates the required relationship between answer
        and user/comment
        """
        form.instance.user = self.request.user
        form.instance.answer_id = self.kwargs['answer_id']
        return super(CreateAnswerCommentView, self).form_valid(form)

    def get_success_url(self):
        question_pk = Answer.objects.get(
            id=self.kwargs['answer_id']).question.pk
        return reverse('qa_detail', kwargs={'pk': question_pk})


class CreateQuestionCommentView(LoginRequired, CreateView):
    """
    View to create new comments for a given question
    """
    template_name = 'qa/create_comment.html'
    model = QuestionComment
    fields = ['comment_text']

    def form_valid(self, form):
        """
        Creates the required relationship between question
        and user/comment
        """
        form.instance.user = self.request.user
        form.instance.question_id = self.kwargs['question_id']
        return super(CreateQuestionCommentView, self).form_valid(form)

    def get_success_url(self):
        return reverse('qa_detail', kwargs={'pk': self.kwargs['question_id']})


class UpdateQuestionCommentView(LoginRequired, UpdateView):
    """
    Updates the comment question
    """
    template_name = 'qa/create_comment.html'
    model = QuestionComment
    pk_url_kwarg = 'comment_id'
    fields = ['comment_text']

    def get_success_url(self):
        question_comment = self.get_object()
        return reverse(
            'qa_detail', kwargs={'pk': question_comment.question.pk})


class UpdateAnswerCommentView(UpdateQuestionCommentView):
    """
    Updates the comment answer
    """
    model = AnswerComment

    def get_success_url(self):
        answer_comment = self.get_object()
        return reverse(
            'qa_detail', kwargs={'pk': answer_comment.answer.question.pk})


class QuestionDetailView(DetailView):
    """
    View to call a question and to render all the details about that question.
    """
    model = Question
    template_name = 'qa/detail_question.html'
    context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super(QuestionDetailView, self).get_context_data(**kwargs)
        context['last_comments'] = self.object.questioncomment_set.order_by(
            'pub_date')[:5]
        context['answers'] = self.object.answer_set.all().order_by('pub_date')
        return context

    def get_object(self):
        # Call the superclass
        question = super(QuestionDetailView, self).get_object()
        question.views += 1
        question.save()
        return question


class ParentVoteView(View):
    """
    Base class to create a vote for a given model (question/answer)
    """
    model = None
    vote_model = None

    def get_vote_kwargs(self, user, vote_target):
        """
        This takes the user and the vote and adjusts the kwargs
        depending on the used model.
        """
        object_kwargs = {'user': user}
        if self.model == Question:
            target_key = 'question'
        elif self.model == Answer:
            target_key = 'answer'
        else:
            raise ValidationError('Not a valid model for votes')
        object_kwargs[target_key] = vote_target
        return object_kwargs

    def post(self, request, object_id):
        vote_target = get_object_or_404(self.model, pk=object_id)
        if vote_target.user == request.user:
            raise ValidationError(
                'Sorry, voting for your own answer is not possible.')
        else:
            upvote = request.POST.get('upvote', None) is not None
            object_kwargs = self.get_vote_kwargs(request.user, vote_target)
            vote, created = self.vote_model.objects.get_or_create(
                defaults={'value': upvote},
                **object_kwargs)
            if created:
                vote_target.votes += 1 if upvote else -1
                vote_target.user.userqaprofile.points += 1 if upvote else -1
            elif not created:
                if vote.value == upvote:
                    vote.delete()
                    vote_target.votes += -1 if upvote else 1
                    vote_target.user.userqaprofile.points += -1 if upvote else 1
                else:
                    vote_target.votes += 2 if upvote else -2
                    vote_target.user.userqaprofile.points += 2 if upvote else -2
                    vote.value = upvote
                    vote.save()
            vote_target.user.userqaprofile.save()
            vote_target.save()

        next_url = request.POST.get('next', None)
        if next_url is not None:
            return redirect(next_url)
        else:
            return redirect(reverse('qa_index'))


class AnswerVoteView(ParentVoteView):
    """
    Class to upvote answers
    """
    model = Answer
    vote_model = AnswerVote


class QuestionVoteView(ParentVoteView):
    """
    Class to upvote questions
    """
    model = Question
    vote_model = QuestionVote


def profile(request, user_id):
    user_ob = get_user_model().objects.get(id=user_id)
    user = UserQAProfile.objects.get(user=user_ob)
    return render(request, 'qa/profile.html', {'user': user})
