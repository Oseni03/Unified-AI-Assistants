from django.http import HttpRequest
from django.shortcuts import redirect, get_object_or_404

from rest_framework import status, generics, permissions
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from common.models import State, ThirdParty
from integrations.models import Integration

from .models import Agent, FeedBack
from .serializers import AgentSerializer, FeedBackSerializer
from .utils.google.utils import credentials_to_dict, get_agent


# Create your views here.
class AgentListView(generics.ListAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AgentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(user=self.request.user)

    # @action(
    #     methods=["post", "update", "delete"],
    #     detail=True,
    #     serializer_class=FeedBackSerializer,
    # )
    # def feedback(self, request, id=None, *args, **kwargs):
    #     if request.method == "POST":
    #         serializer = FeedBackSerializer(data=request.data)
    #         serializer.save(agent=self.get_object())
    #     elif request.method == "PUT":
    #         feedback = get_object_or_404(FeedBack, id=id)
    #         serializer = FeedBackSerializer(feedback, data=request.data)
    #         if serializer.is_valid():
    #             serializer.save()
    #     elif request.method == "DELETE":
    #         feedback = get_object_or_404(FeedBack, id=id).delete()
    #         return Response({}, status=status.HTTP_204_NO_CONTENT)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


class OAuthAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, thirdparty, **kwargs):
        gen_state = State().issue(thirdparty)
        request.session["thirdparty"] = thirdparty  # Add to the session
        request.session["state"] = gen_state  # Add to the session

        integration = Integration.objects.get(thirdparty=thirdparty)
        auth_url = integration.get_oauth_url(
            state=gen_state, user_email=request.user.email
        )
        print(auth_url)
        return redirect(auth_url)


class OAuthCallBackAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSerializer

    def get(self, request: HttpRequest, **kwargs):
        if request.GET.get("code", None):
            try:
                # Ensure that the request is not a forgery and that the user sending
                # this connect request is the expected user.
                gen_state = request.session.get("state")
                thirdparty = request.session.get("thirdparty")

                state = request.GET.get("state", "")
                code = request.GET.get("code", "")

                print(f"State: {state}\nCode: {code}\nThirdparty: {thirdparty}")

                if not (state == gen_state):
                    return Response(
                        "Invalid state parameter.", status=status.HTTP_401_UNAUTHORIZED
                    )

                State.consume(state)

                integration = Integration.objects.get(thirdparty=thirdparty)
                credentials = integration.handle_oauth_callback(state, code)
                print(credentials)

                print(credentials_to_dict(credentials))
                agent = Agent(
                    user=request.user,
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_uri=credentials.token_uri,
                    integration=integration,
                    scopes_text=", ".join(credentials.scopes),
                )
                agent.save()

                serializer = self.get_serializer(instance=agent)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except:
                error = request.GET.get("error", "")
                return Response(
                    f"Something is wrong with the installation (error: {str(error)})",
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            error = request.GET.get("error")
            if error == "access_denied":
                return Response(
                    {"message": "Access denied!"}, status=status.HTTP_204_NO_CONTENT
                )
            elif error == "admin_policy_enforced":
                return Response(
                    {
                        "message": "The Google Account is unable to authorize one or more scopes requested due to the policies of their Google Workspace administrator."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {
                        "message": "Invalid request."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
