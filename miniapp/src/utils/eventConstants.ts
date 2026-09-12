/**
 * 全局事件 action 常量 — 跨文件共享，消除字符串字面量
 *
 * 命名规范：{模块}_{动作} snake_case
 * 消歧前缀：diary_/gear_/weight_ 区分同名 offline_create_pending
 */
export const EV = {
  // --- auth.ts ---
  LOGIN_START: 'login_start',
  LOGIN_SUCCESS: 'login_success',
  LOGIN_FAILED: 'login_failed',
  PROFILE_UPDATE: 'profile_update',
  ENSURE_LOGIN_FAILED: 'ensure_login_failed',

  // --- diary.ts ---
  DIARY_CREATE: 'diary_create',
  DIARY_CREATED: 'diary_created',
  DIARY_CREATE_FAILED: 'diary_create_failed',
  DIARY_UPDATE: 'diary_update',
  DIARY_UPDATED: 'diary_updated',
  DIARY_UPDATE_FAILED: 'diary_update_failed',
  DIARY_DELETE: 'diary_delete',
  DIARY_DELETED: 'diary_deleted',
  DIARY_DELETE_FAILED: 'diary_delete_failed',
  DIARY_DETAIL_LOAD: 'diary_detail_load',
  DIARY_DETAIL_LOAD_FAILED: 'diary_detail_load_failed',
  DIARY_OFFLINE_CREATE_PENDING: 'diary_offline_create_pending',

  // --- gear.ts ---
  GEAR_CREATE: 'gear_create',
  GEAR_CREATED: 'gear_created',
  GEAR_CREATE_FAILED: 'gear_create_failed',
  GEAR_UPDATE: 'gear_update',
  GEAR_UPDATED: 'gear_updated',
  GEAR_UPDATE_FAILED: 'gear_update_failed',
  GEAR_DELETE: 'gear_delete',
  GEAR_DELETED: 'gear_deleted',
  GEAR_DELETE_FAILED: 'gear_delete_failed',
  GEAR_DETAIL_LOAD: 'gear_detail_load',
  GEAR_DETAIL_LOAD_FAILED: 'gear_detail_load_failed',
  GEAR_OFFLINE_CREATE_PENDING: 'gear_offline_create_pending',

  // --- gear/form.vue photo flow ---
  GEAR_PHOTO_CHOOSE: 'gear_photo_choose',
  GEAR_PHOTO_GUEST_CHECK_FAILED: 'gear_photo_guest_check_failed',
  GEAR_PHOTO_GUEST_CHECKED: 'gear_photo_guest_checked',
  GEAR_PHOTO_OFFLINE_LOCAL: 'gear_photo_offline_local',
  GEAR_PHOTO_MIRAGE: 'gear_photo_mirage',
  GEAR_PHOTO_UPLOAD_SUCCESS: 'gear_photo_upload_success',
  GEAR_PHOTO_SELECTED: 'gear_photo_selected',
  GEAR_PHOTO_FAILED: 'gear_photo_failed',

  // --- weight.ts ---
  WEIGHT_CREATE: 'weight_create',
  WEIGHT_CREATED: 'weight_created',
  WEIGHT_CREATE_FAILED: 'weight_create_failed',
  WEIGHT_DELETE: 'weight_delete',
  WEIGHT_DELETED: 'weight_deleted',
  WEIGHT_DELETE_FAILED: 'weight_delete_failed',
  WEIGHT_OFFLINE_CREATE_PENDING: 'weight_offline_create_pending',

  // --- settings.ts ---
  THEME_CHANGE: 'theme_change',

  // --- analysis.ts ---
  ANALYSIS_LIST_OFFLINE: 'analysis_list_offline',
  ANALYSIS_LIST_LOAD_FAILED: 'analysis_list_load_failed',

  // --- sync.ts ---
  PENDING_SYNC_DONE: 'pending_sync_done',
  OFFLINE_SYNC_DONE: 'offline_sync_done',
  OFFLINE_SYNC_FAILED: 'offline_sync_failed',

  // --- stats.vue ---
  STATS_GUEST_LOCAL: 'stats_guest_local',
  STATS_LOAD: 'stats_load',
  STATS_LOADED: 'stats_loaded',
  STATS_OFFLINE_FALLBACK: 'stats_offline_fallback',
  STATS_LOAD_FAILED: 'stats_load_failed',

  // --- share.vue ---
  SHARE_LOAD_DIARIES_START: 'share_load_diaries_start',
  SHARE_LOAD_ANALYSES_START: 'share_load_analyses_start',
  SHARE_LOAD_DIARIES_SUCCESS: 'share_load_diaries_success',
  SHARE_LOAD_ANALYSES_SUCCESS: 'share_load_analyses_success',
  SHARE_DATA_LOAD_FAILED: 'share_data_load_failed',
  SHARE_QR_LOAD_FAILED: 'share_qr_load_failed',
  SHARE_PERSIST_SAVE_FAILED: 'share_persist_save_failed',
  SHARE_CANVAS_FAILED: 'share_canvas_failed',
  SHARE_CAPTION_AI: 'share_caption_ai',
  SHARE_CAPTION_AI_FAILED: 'share_caption_ai_failed',
  CAPTION_COPIED: 'caption_copied',
  SHARE_IMAGE_SAVE: 'share_image_save',
  SHARE_IMAGE_SAVED: 'share_image_saved',
  SHARE_IMAGE_DENIED: 'share_image_denied',
  SHARE_IMAGE_FAILED: 'share_image_failed',

  // --- mine.vue ---
  MINE_STATS_LOAD: 'mine_stats_load',
  MINE_STATS_LOADED: 'mine_stats_loaded',
  MINE_STATS_LOAD_FAILED: 'mine_stats_load_failed',
  MINE_SYNC_FAILED: 'mine_sync_failed',

  // --- profile-edit.vue ---
  PRIVACY_NICKNAME_REQUEST: 'privacy_nickname_request',
  PRIVACY_NICKNAME_AGREE: 'privacy_nickname_agree',
  PRIVACY_NICKNAME_DENIED: 'privacy_nickname_denied',
  PRIVACY_NICKNAME_ERROR: 'privacy_nickname_error',
  AVATAR_UPDATE_START: 'avatar_update_start',
  AVATAR_UPLOAD_START: 'avatar_upload_start',
  AVATAR_UPLOAD_SUCCESS: 'avatar_upload_success',
  AVATAR_UPLOAD_FAILED: 'avatar_upload_failed',
  PROFILE_SAVE_AVATAR_START: 'profile_save_avatar_start',
  PROFILE_SAVE_AVATAR_SUCCESS: 'profile_save_avatar_success',
  PROFILE_SAVE_AVATAR_FAILED: 'profile_save_avatar_failed',
  AVATAR_UPDATE_COMPLETE: 'avatar_update_complete',
  LOGOUT_START: 'logout_start',
  LOGOUT: 'logout',

  // --- report.vue ---
  REPORT_OFFLINE: 'report_offline',
  REPORT_LOAD: 'report_load',
  REPORT_LOADED: 'report_loaded',
  REPORT_SUBSCRIBE_START: 'report_subscribe_start',
  REPORT_LOAD_FAILED: 'report_load_failed',
  REPORT_RELOAD_FAILED: 'report_reload_failed',
  ANALYSIS_DELETE: 'analysis_delete',
  ANALYSIS_DELETED: 'analysis_deleted',
  ANALYSIS_DELETE_FAILED: 'analysis_delete_failed',

  // --- request.ts (network layer) ---
  API_ERROR: 'api_error',
  HTTP_ERROR: 'http_error',
  HTTP_WARN: 'http_warn',
  NETWORK_ERROR: 'network_error',
} as const
