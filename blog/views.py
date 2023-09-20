from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import (
    SearchVector,
    SearchQuery,
    SearchRank,
    TrigramSimilarity,
)


# Function based post list view
def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get("page", 1)
    try:
        posts = paginator.page(page_number)
    except EmptyPage:
        # If page_number is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        # if page_number is not an integer deliver the first page
        posts = paginator.page(1)

    return render(
        request,
        "blog/post/list.html",
        {
            "posts": posts,
            "tag": tag,
        },
    )


# Class based view to list posts
# class PostListView(ListView):
#     """
#     Alternative post list view
#     """

#     # model = Post
#     # queryset = Post.objects.filter(status=Post.Status.PUBLISHED)

#     queryset = Post.published.all()
#     context_object_name = "posts"
#     paginate_by = 3
#     template_name = "blog/post/list.html"


# Function based post detail view
def post_detail(request, year, month, day, post):
    # try:
    #     post = Post.objects.get(id=id)
    # except Post.DoesNotExist:
    #     raise Http404("No Post found")

    # Using get() function that raise Http404 exception instead of
    # DoesNotExist when no object is found on default objects model manager
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    # List of active comments for this post
    comments = post.comments.filter(active=True)
    # Form for users to commit
    form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-publish"
    )[:4]

    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "form": form,
            "similar_posts": similar_posts,
        },
    )


# Email form handling view
def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False

    if request.method == "POST":
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            # Send email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read {post.title}"
            message = f"Read {post.title} at {post_url}\n\n {cd['name']}'s comments: {cd['comments']}"
            send_mail(subject, message, "your_account@gmail.com", [cd["to"]])
            sent = True
    else:
        form = EmailPostForm()
    return render(
        request,
        "blog/post/share.html",
        {
            "post": post,
            "form": form,
            "sent": sent,
        },
    )


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None
    # A comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create a comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the commit  to the database
        comment.save()
    return render(
        request,
        "blog/post/comment.html",
        {
            "post": post,
            "form": form,
            "comment": comment,
        },
    )


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]

            # Stemming and ranking results
            # search_vector = SearchVector("title", "body")
            # search_query = SearchQuery(query)
            # results = (
            #     Post.published.annotate(
            #         search=search_vector, rank=SearchRank(search_vector, search_query)
            #     )
            #     .filter(search=search_query)
            #     .order_by("-rank")
            # )

            # Stemming and removing stop words in different languages
            # search_vector = SearchVector("title", "body", config="spanish")
            # search_query = SearchQuery(query, config="spanish")
            # results = (
            #     Post.published.annotate(
            #         search=search_vector, rank=SearchRank(search_vector, search_query)
            #     )
            #     .filter(search=search_query)
            #     .order_by("-rank")
            # )

            # Weighting queries
            search_vector = SearchVector("title", weight="A") + SearchVector(
                "body", weight="B"
            )
            search_query = SearchQuery(query)
            results = (
                Post.published.annotate(
                    search=search_vector, rank=SearchRank(search_vector, search_query)
                )
                .filter(rank__gte=0.3)
                .order_by("-rank")
            )

            # Searching with trigram similarity
            # results = (
            #     Post.published.annotate(
            #         similarity=TrigramSimilarity("title", query),
            #     )
            #     .filter(similarity__gt=0.1)
            #     .order_by("-similarity")
            # )
    return render(
        request,
        "blog/post/search.html",
        {"form": form, "query": query, "results": results},
    )
