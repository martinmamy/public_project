from django.urls import path


from MindBridge.views.admin_views import AdminSendEmailView
from MindBridge.views.ads_views import (
    DeleteAdView,
    EditDraftAdView,
    EnableRecurringAdView,
    ProblemAdsView,
    CreateAdView, CreateAdPaymentView, AdPaymentSuccessView,
    AdvertiserDashboardView, AdminAdsDashboardView, AdClickView,
    ProblemSponsoredAdsView,
    RelaunchAdView,
    SaveAdDraftView,
    StopRecurringAdView,
    
)

from MindBridge.views.auth_views import (
    DeleteProfileView,
    ExpertSearchView,
    ForgotPasswordView,
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ReportUserView,
    ResendOTPView,
    ResetPasswordView,
    SendEmailChangeOTPView,
    ToggleVerificationRecurringView,
    UpdateAvailabilityView,
    UpdateEmailView,
    UpdateProfileView, ProfileActivityAPI,
    VerifyDeletePasswordView,
    VerifyEmailChangeOTPView,
    VerifyEmailView,
    VerifyOTPView,
    VerifyPasswordAjax,
    VerifyPasswordResetOTPView
)

from MindBridge.views.data_processing import FAQView, PrivacyPartialView, PrivacyView, TermsPartialView, TermsView, TransparentInfo
from MindBridge.views.feed_views import (
    GlobalFeedView,
    PersonalizedFeedView, 
    TrendingFeedView, FeedsPageView, ProblemIncrementView,
)
from MindBridge.views.home_views import HomePageView, settingsPageView
from MindBridge.views.knowledgebase_views import KnowledgeBaseView
from MindBridge.views.problem_views import (
    CreateProblemView,
    ListProblemsView,
    ProblemDetailView,
    TalentHubView,
    TrendingProblemsView,
    DeleteProblemView,
    UpdateProblemView,
    get_problem_answers,
    toggle_bookmark,toggle_talenthub_bookmark,
    PromoteProblemView,
)

from MindBridge.views.answer_views import (
    CreateAnswerView,
    AcceptAnswerView,
    DeleteAnswerView,
    UpdateAnswerView,
    generate_ai_answer,
)

from MindBridge.views.comment_views import (
    CreateCommentView,
    DeleteProblemCommentView, 
    EditAnswerCommentView, 
    DeleteAnswerCommentView,
    EditProblemCommentView,
    ProblemCommentsView,
    AnswerCommentsView
)

from MindBridge.views.reporting_views import(
    PaymentReportView, download_user_report,
)

from MindBridge.views.session_views import AvailabilitySlotCreateView, BookingCancelView, BookingCreateView, SlotDeleteView, SlotEventsAPIView, SlotListView, SlotUpdateView
from MindBridge.views.translator_views import TranslateContentView
from MindBridge.views.vote_views import (
    VoteProblemView,
    VoteAnswerView,
)

from MindBridge.views.follow_views import (
    FollowUserView,
    UnfollowUserView, ProfileFollowersAPI,
    ProfileFollowingAPI,
)

from MindBridge.views.tip_views import (
    SendProblemTipView, SendTipView,
)

from MindBridge.views.notification_views import (
    NotificationsListView, MarkReadView, MarkAllReadView, DeleteNotificationView, NotificationsApiView, NotificationsPageView, SavePushSubscriptionView,
)
from MindBridge.views.user_suggestion_views import(
    UserSuggestionView,
)
from MindBridge.views.events_views import (
    CreateEventView,
    EventHubCreateView,
    EventHubDeleteView,
    EventHubListView,
    EventHubUpdateView,
    EventListView,
    EventDetailView,
    JoinEventView,
    InviteUserToEventView,
    AcceptEventInviteView,
    SetEventReminderView,
    StartLiveEventView,
    StopLiveEventView,
    LiveEventListView,
    InternalLiveStreamView,
    SaveRecordingView,
    DeleteRecordingView,
    DeleteEventView,
    LeaveEventView,
)

from MindBridge.views.payment_views import(
    PayPalAccountLinkedErrorView, PayPalAccountLinkedView, 
    PayPalCallbackView, LinkPayPalAccountView, LinkPaymentAccountView,
)
from MindBridge.views.expert_verify_views import (
    VerifyExpertView, 
    AjaxVerifyExpertView,
    
)
from MindBridge.views.maintenance import (MaintenancePageView, MissingDataPageView, TemplateView,)

from MindBridge.views.subscription_views import (
    CreateSubscriptionAPIView,
    CancelSubscriptionAPIView,
    PayPalWebhookAPIView,
    PayPalSubscriptionSuccessView,
    PayPalSubscriptionCancelView,
    SubscriptionCheckoutPageView,
)

urlpatterns = [

    # =========================
    # AUTH
    # =========================
    path('maintenance/', MaintenancePageView.as_view(), name='maintenance_page'),
    path('missing-data/', MissingDataPageView.as_view(), name='missing_page_dev'),
    path('missing-page/', TemplateView.as_view(template_name="missing_page.html"), name='missing_page'),
    path("", HomePageView.as_view(), name="home"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/resend-otp/", ResendOTPView.as_view(), name="resend_otp"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("auth/faq/", FAQView.as_view(), name="faq"),
    path("auth/profile/<uuid:user_id>/", ProfileView.as_view(), name="profile"),
    path("auth/profile/update/", UpdateProfileView.as_view(), name="update_profile"),
    path('auth/profile/<uuid:user_id>/activity/', ProfileActivityAPI.as_view(), name='profile_activity_api'),
    path(
        "auth/forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot_password"
    ),

    path(
        "auth/verify-password-reset/",
        VerifyPasswordResetOTPView.as_view(),
        name="verify_password_reset_otp"
    ),

    path(
        "auth/reset-password/",
        ResetPasswordView.as_view(),
        name="reset_password"
    ),
    path(
        "auth/profile/availability/<int:pk>/",
        UpdateAvailabilityView.as_view(),
        name="update_availability"
    ),
    # urls.py
    path("auth/profile/experts/", ExpertSearchView.as_view(), name="expert_search"),
    path(
        "auth/profile/delete/",
        DeleteProfileView.as_view(),
        name="delete_profile"
    ),
    path(
        "verify-delete-password/",
        VerifyDeletePasswordView.as_view(),
        name="verify_delete_password"
    ),
    path("ajax/verify-password/", VerifyPasswordAjax.as_view(), name="verify_password_ajax"),
    path("ajax/verify-email-otp/", VerifyEmailChangeOTPView.as_view(), name="verify_email_otp"),
    path("update-email/", UpdateEmailView.as_view(), name="update_email"),
    path("ajax/send-email-otp/", SendEmailChangeOTPView.as_view(), name="send_new_email_otp"),

        
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("terms/", TermsView.as_view(), name="terms"),
    
    path("privacy/partial/", PrivacyPartialView.as_view(), name="privacy_partial"),
    path("terms/partial/", TermsPartialView.as_view(), name="terms_partial"),
    path("transparent-info/", TransparentInfo.as_view(), name="transparent_info"),
    
    # =========================
    # PROBLEMS
    # =========================
    path("problems/create/", CreateProblemView.as_view(), name="create_problem"),
    path("problems/", ListProblemsView.as_view(), name="list_problems"),
    path("problems/trending/", TrendingProblemsView.as_view(), name="trending_problems"),
    path("problems/update/<uuid:problem_id>/", UpdateProblemView.as_view(), name="update_problem"),
    path("problems/delete/<uuid:problem_id>/", DeleteProblemView.as_view(), name="delete_problem"),
    
    path("talenthub/", TalentHubView.as_view(), name="talenthub"),

    path(
        "problems/<uuid:problem_id>/",
        ProblemDetailView.as_view(),
        name="problem_detail"
    ),
    path(
        "problems/<uuid:problem_id>/partial/",
        ProblemDetailView.as_view(template_name="problem_detail_partial.html"),
        name="problem_detail_partial"
    ),


    # =========================
    # ANSWERS
    # =========================
    path("answers/create/<uuid:problem_id>/", CreateAnswerView.as_view(), name="create_answer"),

    path("answers/update/<uuid:answer_id>/", UpdateAnswerView.as_view(), name="update_answer"),

    path("answers/delete/<uuid:answer_id>/", DeleteAnswerView.as_view(), name="delete_answer"),

    path("answers/accept/<uuid:answer_id>/", AcceptAnswerView.as_view(), name="accept_answer"),
    
    path('answers/generate_ai_answer/<uuid:problem_id>/', generate_ai_answer, name='generate_ai_answer'),
    path("answers/problem/<uuid:problem_id>/", get_problem_answers),

    # =========================
    # COMMENTS
    # =========================
    path('comments/create/', CreateCommentView.as_view(), name='create_comment'),
    path('problems/<uuid:problem_id>/comments/', ProblemCommentsView.as_view(), name='problem_comments'),
    path('answers/<uuid:answer_id>/comments/', AnswerCommentsView.as_view(), name='answer_comments'),

    path(
        "comments/problem/<uuid:comment_id>/edit/",
        EditProblemCommentView.as_view(),
        name="edit_problem_comment"
    ),

    path(
        "comments/problem/<uuid:comment_id>/delete/",
        DeleteProblemCommentView.as_view(),
        name="delete_problem_comment"
    ),

    path(
        "comments/answer/<uuid:comment_id>/edit/",
        EditAnswerCommentView.as_view(),
        name="edit_answer_comment"
    ),

    path(
        "comments/answer/<uuid:comment_id>/delete/",
        DeleteAnswerCommentView.as_view(),
        name="delete_answer_comment"
    ),

    path("api/user_suggest/", UserSuggestionView.as_view(), name="user_suggest"),
    # =========================
    # VOTING
    # =========================
    path(
        "vote/problem/<uuid:problem_id>/",
        VoteProblemView.as_view(),
        name="vote_problem"
    ),

    path(
        "vote/answer/<uuid:answer_id>/",
        VoteAnswerView.as_view(),
        name="vote_answer"
    ),

    path('problems/<uuid:problem_id>/save/', toggle_bookmark, name='toggle_bookmark'),
    path('problems/talenthub/<uuid:problem_id>/save/', toggle_talenthub_bookmark, name='toggle_talenthub_bookmark'),
    
    # =========================
    # SOCIAL
    # =========================
    path(
        "users/<uuid:user_id>/follow/",
        FollowUserView.as_view(),
        name="follow_user"
    ),

    path(
        "users/<uuid:user_id>/unfollow/",
        UnfollowUserView.as_view(),
        name="unfollow_user"
    ),
    # Followers / Following APIs
    path('user/<uuid:user_id>/followers/', ProfileFollowersAPI.as_view(), name='profile_followers_api'),
    path('user/<uuid:user_id>/following/', ProfileFollowingAPI.as_view(), name='profile_following_api'),

    # =========================
    # MONETIZATION
    # =========================
    path(
        "answers/<uuid:answer_id>/tip/",
        SendTipView.as_view(),
        name="send_tip"
    ),
     
    
    

    # =========================
    # NOTIFICATIONS
    # =========================
    path('notifications/', NotificationsListView.as_view(), name='notifications_list'),
    path('notifications/mark_read/<int:notif_id>/', MarkReadView.as_view(), name='mark_read'),
    path('notifications/mark_all_read/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('notifications/delete/<int:notif_id>/', DeleteNotificationView.as_view(), name='delete_notification'),
    path("notifications/api/", NotificationsApiView.as_view(), name="notifications_api"),
    path("notifications-page/", NotificationsPageView.as_view(), name="notifications_page"),
    path(
        "push/save/",
        SavePushSubscriptionView.as_view(),
        name="push_save"
    ),
    
    # -----------------------------
    # Feeds Page (all feeds)
    # -----------------------------
    path("feeds/", FeedsPageView.as_view(), name="feeds"),

    # -----------------------------
    # API / JSON Endpoints
    # -----------------------------
    path("feeds/global/", GlobalFeedView.as_view(), name="global_feed"),
    path("feeds/trending/", TrendingFeedView.as_view(), name="trending_feed"),
    path("feeds/personalized/", PersonalizedFeedView.as_view(), name="personalized_feed"),

    # -----------------------------
    # Increment views AJAX endpoint
    # -----------------------------
    path('feeds/increment/<uuid:problem_id>/', ProblemIncrementView.as_view(), name='increment_views'),
    
    # Tip an answer
    path("answers/<uuid:answer_id>/tip/", SendTipView.as_view(), name="send_answer_tip"),

    # Tip a problem  
    path("problems/<uuid:problem_id>/tip/", SendProblemTipView.as_view(), name="send_problem_tip"),
    
    
    # -------------------------
    # EVENT LIST / CREATE
    # -------------------------
    path("events/", EventListView.as_view(), name="event_list"),
    path("events/create/", CreateEventView.as_view(), name="create_event"),

    # -------------------------
    # LIVE EVENTS PAGE
    # -------------------------
    path("events/live/", LiveEventListView.as_view(), name="live_events"),

    # -------------------------
    # EVENT DETAIL
    # -------------------------
    path("events/<uuid:event_id>/", EventDetailView.as_view(), name="event_detail"),

    # -------------------------
    # JOIN EVENT
    # -------------------------
    path("events/<uuid:event_id>/join/", JoinEventView.as_view(), name="join_event"),

    # -------------------------
    # START / STOP LIVE
    # -------------------------
    path("events/<uuid:event_id>/start-live/", StartLiveEventView.as_view(), name="start_live_event"),
    path("events/<uuid:event_id>/stop-live/", StopLiveEventView.as_view(), name="stop_live_event"),
    path('events/<uuid:event_id>/leave/', LeaveEventView.as_view(), name='leave_event'),

    # -------------------------
    # INVITATIONS
    # -------------------------
    path("events/<uuid:event_id>/invite/", InviteUserToEventView.as_view(), name="invite_user_event"),
    path("events/invite/<uuid:invite_id>/accept/", AcceptEventInviteView.as_view(), name="accept_event_invite"),

    # -------------------------
    # STREAM VIDEO
    # -------------------------
    path("events/<uuid:event_id>/stream/", InternalLiveStreamView.as_view(), name="event_stream"),

    # -------------------------
    # RECORDINGS
    # -------------------------
    path("events/<uuid:event_id>/save-recording/", SaveRecordingView.as_view(), name="save_recording"),
    path("recordings/<uuid:pk>/delete/", DeleteRecordingView.as_view(), name="delete_recording"),

    # -------------------------
    # DELETE EVENT
    # -------------------------
    path("events/<uuid:event_id>/delete/", DeleteEventView.as_view(), name="delete_event"),# -------------------------
    # EVENT LIST / CREATE
    # -------------------------
    path("events/", EventListView.as_view(), name="event_list"),
    path("events/create/", CreateEventView.as_view(), name="create_event"),

    # -------------------------
    # LIVE EVENTS PAGE
    # -------------------------
    path("events/live/", LiveEventListView.as_view(), name="live_events"),

    # -------------------------
    # EVENT DETAIL
    # -------------------------
    path("events/<uuid:event_id>/", EventDetailView.as_view(), name="event_detail"),

    # -------------------------
    # JOIN EVENT
    # -------------------------
    path("events/<uuid:event_id>/join/", JoinEventView.as_view(), name="join_event"),

    # -------------------------
    # START / STOP LIVE
    # -------------------------
    path("events/<uuid:event_id>/start-live/", StartLiveEventView.as_view(), name="start_live_event"),
    path("events/<uuid:event_id>/stop-live/", StopLiveEventView.as_view(), name="stop_live_event"),

    # -------------------------
    # INVITATIONS
    # -------------------------
    path("events/<uuid:event_id>/invite/", InviteUserToEventView.as_view(), name="invite_user_event"),
    path("events/invite/<uuid:invite_id>/accept/", AcceptEventInviteView.as_view(), name="accept_event_invite"),

    # -------------------------
    # STREAM VIDEO
    # -------------------------
    path("events/<uuid:event_id>/stream/", InternalLiveStreamView.as_view(), name="event_stream"),

    # -------------------------
    # RECORDINGS
    # -------------------------
    path("events/<uuid:event_id>/save-recording/", SaveRecordingView.as_view(), name="save_recording"),
    path("recordings/<uuid:pk>/delete/", DeleteRecordingView.as_view(), name="delete_recording"),

    # -------------------------
    # DELETE EVENT
    # -------------------------
    path("events/<uuid:event_id>/delete/", DeleteEventView.as_view(), name="delete_event"),
    
    
    path("events/hub/", EventHubListView.as_view(), name="eventhub_list"),

    path("events/hub/create/", EventHubCreateView.as_view(), name="eventhub_create"),

    # FIX: MUST be UpdateView (not CreateView)
    path("events/hub/<uuid:pk>/edit/", EventHubUpdateView.as_view(), name="eventhub_update"),

    path("events/hub/<uuid:pk>/delete/", EventHubDeleteView.as_view(), name="eventhub_delete"),
    path(
        "events/hub/<uuid:event_id>/reminder/",
        SetEventReminderView.as_view(),
        name="set_event_reminder"
    ),
    
    path(
        "payments/link/",
        LinkPaymentAccountView.as_view(),
        name="link_payment_account"
    ),

    path(
        "payments/paypal/connect/",
        LinkPayPalAccountView.as_view(),
        name="link_paypal_account"
    ),

    path(
        "payments/paypal/callback/",
        PayPalCallbackView.as_view(),
        name="paypal_callback"
    ),

    path(
        "payments/paypal/success/",
        PayPalAccountLinkedView.as_view(),
        name="paypal_account_linked"
    ),

    path(
        "payments/paypal/error/",
        PayPalAccountLinkedErrorView.as_view(),
        name="paypal_account_linked_error"
    ),
    
    path(
        "problem/<uuid:problem_id>/promote/",
        PromoteProblemView.as_view(),
        name="promote_problem"
    ),
    
    path('verify-expert/', VerifyExpertView.as_view(), name='verify_expert'),
    path("ajax/verify-expert/<uuid:user_id>/", AjaxVerifyExpertView.as_view(), name="ajax_verify_expert"),

    path("ads/<uuid:problem_id>/", ProblemAdsView.as_view(), name="problem_ads"),
    path("ads/<uuid:problem_id>/sponsored/", ProblemSponsoredAdsView.as_view(), name="problem_sponsored_ads"),
    
    path("ads/create/", CreateAdView.as_view(), name="create_ad"),
    path("ads/create/payment/<uuid:ad_id>/", CreateAdPaymentView.as_view(), name="create_ad_payment"),
    path("ads/payment/success/<uuid:ad_id>/", AdPaymentSuccessView.as_view(), name="ad_payment_success"),

    path("ads/dashboard/", AdvertiserDashboardView.as_view(), name="ads_dashboard"),
    path("ads/dashboard/admin/", AdminAdsDashboardView.as_view(), name="admin_dashboard"),

    path("ads/<uuid:ad_id>/click/", AdClickView.as_view(), name="ad_click"),
    
    path("ads/save-draft/", SaveAdDraftView.as_view(), name="save_ad_draft"),
    
    # ============================================
    # EDIT DRAFT
    # ============================================
    path(
        "ads/<uuid:ad_id>/edit/",
        EditDraftAdView.as_view(),
        name="edit_draft_ad"
    ),

    # ============================================
    # RELAUNCH
    # ============================================
    path(
        "ads/<uuid:ad_id>/relaunch/",
        RelaunchAdView.as_view(),
        name="relaunch_ad"
    ),

    # ============================================
    # ENABLE RECURRING
    # ============================================
    path(
        "ads/<uuid:ad_id>/enable-recurring/",
        EnableRecurringAdView.as_view(),
        name="enable_recurring_ad"
    ),

    # ============================================
    # STOP RECURRING
    # ============================================
    path(
        "ads/<uuid:ad_id>/stop-recurring/",
        StopRecurringAdView.as_view(),
        name="stop_recurring_ad"
    ),

    # ============================================
    # DELETE
    # ============================================
    path(
        "ads/<uuid:ad_id>/delete/",
        DeleteAdView.as_view(),
        name="delete_ad"
    ),
    
    path("reports/user/<uuid:user_id>/pdf/", download_user_report, name="download_user_report"),
    path("reports/payments/", PaymentReportView.as_view(), name="payment_report"),
    
    path("knowledge-base/", KnowledgeBaseView.as_view(), name="knowledge_base"),
    
    
    # list
    # =====================================
    # 📋 MAIN LIST (ALL ACTIONS HAPPEN HERE)
    # =====================================
    path('slots/<uuid:user_id>/', SlotListView.as_view(), name='slot_list'),

    # =====================================
    # 👨‍💻 CREATE SLOT PAGE (only create)
    # =====================================
    path('slots/create/', AvailabilitySlotCreateView.as_view(), name='slot_create'),

    # =====================================
    # ✏️ INLINE UPDATE (POST ONLY)
    # =====================================
    path('slots/<uuid:pk>/update/', SlotUpdateView.as_view(), name='slot_update'),

    # =====================================
    # 🗑 INLINE DELETE (POST ONLY)
    # =====================================
    path('slots/<uuid:pk>/delete/', SlotDeleteView.as_view(), name='slot_delete'),

    # =====================================
    # 📅 BOOK SLOT (POST ONLY)
    # =====================================
    path('slots/<uuid:slot_id>/book/', BookingCreateView.as_view(), name='book_slot'),
    
    path("booking/cancel/<uuid:booking_id>/", BookingCancelView.as_view(), name="cancel_booking_by_slot"),
    
    path("slots/api/", SlotEventsAPIView.as_view(), name="slot_events_api"),
    
    # =====================================
    # ADMIN - SEND EMAIL
    # =====================================
    path("send-email/", AdminSendEmailView.as_view(), name="admin_send_email"),
    path("settings/", settingsPageView.as_view(), name="settings_page"),
    
    path(
        "report-user/",
        ReportUserView.as_view(),
        name="report_user"
    ),
    
    
    # =====================================================
    # PLATFORM SUBSCRIPTION FLOW
    # =====================================================

    path(
        "subscribe/",
        CreateSubscriptionAPIView.as_view(),
        name="create-subscription",
    ),

    path(
        "subscriptions/<uuid:uuid>/cancel/",
        CancelSubscriptionAPIView.as_view(),
        name="cancel-subscription",
    ),

    # =====================================================
    # PAYPAL
    # =====================================================

    path(
        "paypal/webhooks/",
        PayPalWebhookAPIView.as_view(),
        name="paypal-webhooks",
    ),

    path(
        "paypal/success/",
        PayPalSubscriptionSuccessView.as_view(),
        name="paypal-subscription-success",
    ),

    path(
        "paypal/cancel/",
        PayPalSubscriptionCancelView.as_view(),
        name="paypal-subscription-cancel",
    ),

    # =====================================================
    # CHECKOUT PAGE
    # =====================================================

    path(
        "subscriptions/checkout/",
        SubscriptionCheckoutPageView.as_view(),
        name="subscription-checkout",
    ),
    
    path(
        "verification/toggle-recurring/",
        ToggleVerificationRecurringView.as_view(),
        name="toggle_verification_recurring"
    ),
    
    path("ajax/translate/", TranslateContentView.as_view(), name="translate_text"),
]