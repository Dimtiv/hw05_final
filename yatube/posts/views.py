from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

LIMIT = 10


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'posts/index.html', {
        'page_obj': page_obj,
    }
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_group = group.posts.all()
    paginator = Paginator(post_group, LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': page_obj,
    }
    )


def profile(request, username):
    author = User.objects.get(username=username)
    post_author = Post.objects.select_related('author').filter(author=author)
    paginator = Paginator(post_author, LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    count = post_author.count()
    if request.user.is_authenticated and Follow.objects.filter(author=author):
        following = True
    else:
        following = False
    context = {
        'page_obj': page_obj,
        'author': author,
        'count': count,
        'following': following,

    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = Post.objects.get(pk=post_id)
    user = post.author
    count = user.users.count()
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'count': count,
        'comments': comments,
        'form': form
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    form.save()
    return redirect('posts:profile', post.author)


@login_required
def post_edit(request, post_id):
    get_post = get_object_or_404(Post, id=post_id)
    is_edit = True
    if request.user != get_post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        instance=get_post,
        files=request.FILES or None,
    )
    if not form.is_valid():
        return render(
            request, 'posts/create_post.html',
            {'form': form, 'is_edit': is_edit, 'post_id': post_id}
        )
    form.save()
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ...
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = User.objects.get(username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect("posts:profile", username)


@login_required
def profile_unfollow(request, username):
    Follow.objects.filter(
        user=request.user,
        author__username=username).delete()
    return redirect("posts:profile", username)
