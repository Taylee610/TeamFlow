from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from.models import Project, Task
from .forms import TaskForm, ProjectForm

from django.db import IntegrityError
from django.contrib import messages
from django.shortcuts import redirect

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html' 

    def get_queryset(self): 
        return Project.objects.filter(owner=self.request.user)
    
class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_queryset(self):
            return Project.objects.filter(owner=self.request.user)
        
class ProjectDeleteView(LoginRequiredMixin, DeleteView):
        model = Project
        success_url = reverse_lazy('project-list')

        def get_queryset(self):
            return Project.objects.filter(owner=self.request.user)
                    
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.project = get_object_or_404(Project, pk=kwargs[ 'pk'], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
    
    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)
    
    def get_success_url(self):
        print(self.object.pk) 
        return reverse_lazy('project-detail', kwargs={'pk': self.object.pk })
                        
class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'

    def get_queryset(self):
        return Task.objects.filter(project__owner=self.request.user)
    
    def get_success_url(self):
        return self.object.project.get_absolute_url()
                            
class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'projects/task_confirm_delete.html'
class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error('name', 'You already have a project with this name.')
            return self.form_invalid(form)
        
    # def get_success_url(self):
    #     return 


                                
                                
                                