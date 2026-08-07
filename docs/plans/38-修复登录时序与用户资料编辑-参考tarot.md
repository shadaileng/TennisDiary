> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 38 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | 修复「一键登录返回 token 后提示请先登录」时序 bug + 参考 tarot 实现用户资料编辑（头像/昵称/uid 展示/资料修改） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.0.0 | 实施完成（后端登录返回 user + 资料更新 + 头像上传；前端登录修复 + 我的页 + 资料编辑页） |
>
> **关联文档**：[Phase1-8：对接 B1 登录流程](./20-Phase1-8-对接B1登录流程.md) · [Phase2-5：我的页](./31-Phase2-5-我的页.md) · [参考仓库 tarot](https://github.com/shadaileng/tarot)

# Step 38：修复登录时序 bug 与用户资料编辑（参考 tarot）

## 一、背景

### 1.1 问题现象

一键登录点击「微信一键登录」后，后端已返回 `access_token`，但前端却提示「请到『我的』页登录后使用」/「请先登录」，登录流程中断。

### 1.2 根因定位

`auth store` 的 `login()` 采用「先取 token → 再 getMe → 最后 setAuth」三步流程：

```65:80:miniapp/src/stores/auth.ts
    async login() {
      const code = await getLoginCode();
      const token = await loginApi({ code });
      // 换取 token 后再获取用户信息（需携带 Authorization）
      const user = await getMe();
      this.setAuth(token.access_token, user);
      return user;
    },
```

执行时序问题：

1. `loginApi()` 调用 `POST /auth/login`（`auth:false`）拿到 `token`，但**仅存于局部变量，未写入 storage**。
2. 紧接着执行 `getMe()` → `GET /auth/me`（默认 `auth:true`）。此时 `request.ts` 的 `getToken()` 读取 storage 仍为空（`setAuth` 尚未执行）。
3. `request.ts` 未登录门控短路：

```93:97:miniapp/src/services/request.ts
  if (auth && !getToken()) {
    promptLogin();
    return Promise.reject(new ApiError(401, "请先登录"));
  }
```

于是 `getMe()` 直接 rejected → 报「请先登录」，`setAuth()` 永不执行，登录失败。

**即：token 已返回但未持久化，随后的 `getMe()` 被当成「未登录」拦截。**

### 1.3 参考项目 tarot 的做法

tarot 的登录接口 `POST /api/auth/wechat-login` **一次请求同时返回 `{ token, user, isNewUser }`**，前端拿到后立即 `setStoredToken` + `setUserInfo`：

```99:103:docs/reference/tarot/src/services/auth.ts
const result = await apiPost<LoginResult>(API_ENDPOINTS.AUTH.WECHAT_LOGIN, { code: res.code }, { auth: false })
setStoredToken(result.token)
setUserInfo(result.user)
```

**不存在「先 token 后 getMe」的两步竞态**。同时 tarot 提供资料编辑能力：头像 `chooseAvatar` + 上传、昵称 `input type="nickname"`、`PUT /api/user/profile` 更新、uid 脱敏展示 `maskMiddle`。

## 二、目标

1. **根治登录时序 bug**：让 `/api/auth/login` 一次返回 `{ access_token, user, is_new }`，前端拿到即持久化，彻底消除「先 token 后 getMe」竞态。
2. **补齐用户资料编辑能力**（参考 tarot）：头像上传 + 昵称修改 + uid 脱敏展示 + 资料更新接口。
3. **对接「我的」页**：展示头像/昵称/脱敏 uid，支持进入资料编辑。

## 三、方案设计

### 3.1 后端改动

#### 3.1.1 登录接口返回用户信息（`server/app/routers/auth.py`）

改造 `POST /api/auth/login`，响应由 `TokenResponse` 升级为新的 `LoginResponse`（继承 `TokenResponse` + `user` + `is_new`）：

```python
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        openid = await code_to_openid(body.code)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    user = db.query(User).filter(User.openid == openid).first()
    is_new = user is None
    if user is None:
        user = User(openid=openid)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(openid)
    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        is_new=is_new,
    )
```

#### 3.1.2 新增 Schemas（`server/app/schemas/schemas.py`）

在「用户/认证」区块新增：

```python
class UserUpdate(BaseModel):
    """用户资料更新 — 所有字段可选，仅更新传入的字段"""
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=512)


class LoginResponse(TokenResponse):
    user: UserResponse
    is_new: bool = False


class UserUpdateResponse(BaseModel):
    user: UserResponse
```

#### 3.1.3 新增资料更新接口（`server/app/routers/auth.py`）

`PUT /api/auth/me`：需登录，更新昵称/头像，返回最新用户：

```python
@router.put("/me", response_model=UserUpdateResponse)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return UserUpdateResponse(user=UserResponse.model_validate(current_user))
```

> 说明：沿用现有 `UserResponse`/`User` 字段（`id/openid/nickname/avatar_url`）。是否扩展 `gender/birthday/email` 字段作为**可选增强**，见「六、可选增强」；本方案核心仅昵称 + 头像。

#### 3.1.4 新增头像上传接口（新建 `server/app/routers/upload.py`）

参考 tarot 的 `POST /api/upload/avatar` 与现有 `files.py` 的路径安全/归属校验，新增头像上传：

```python
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # 校验图片扩展名（jpg/jpeg/png/webp）
    # 生成唯一文件名（uuid + 扩展名）
    # 保存到 UPLOAD_DIR/avatar/<user_id>/<uuid>.<ext>
    # 返回 {"url": f"avatars/<user_id>/<uuid>.<ext>"} 或完整相对路径
```

返回的 `url` 需能被前端用于 `<image>` 展示。因头像不归属任何 `Gear`，`files.py` 的 `_is_file_owned` 归属校验不适用，故头像通过独立 `upload.py` 存储，并在 `files.py` 下载逻辑中补充「头像文件允许当前用户读取」的判定（或头像直接由前端拼接 BASE_URL 读取）。

> 设计取舍：头像文件归属用户本人。可复用 `files.py` 下载路由，但需扩展 `_is_file_owned` 支持 `User.avatar_url` 归属判断，或头像下载单独走 `upload` 路由的 GET。**推荐**：头像存储路径含 `user_id`，并在 `files.py` 增加「相对路径命中当前用户 `avatar_url` 即允许下载」的判断。

#### 3.1.5 注册新路由（`server/app/main.py`）

```python
from app.routers import auth, checkin, diaries, files, gears, stats, upload, weights
...
app.include_router(upload.router)
```

### 3.2 前端改动

#### 3.2.1 类型（`miniapp/src/types/index.ts`）

新增 `LoginResponse`（含 `user`、`is_new`）与 `UserUpdate` 类型：

```ts
/** 登录响应（后台 LoginResponse） */
export interface LoginResponse extends Token {
  user: User
  is_new: boolean
}

/** 更新用户资料入参（后台 UserUpdate） */
export interface UserUpdate {
  nickname?: string
  avatar_url?: string
}
```

#### 3.2.2 服务层（`miniapp/src/services/auth.ts`）

- `login()` 返回类型改为 `LoginResponse`
- 新增 `updateProfile(data: UserUpdate): Promise<{ user: User }>` → `PUT /auth/me`
- 新增头像上传辅助 `uploadAvatar(tempPath): Promise<string>`（封装 `uni.uploadFile`，返回 url）

```ts
export function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/login", data, { auth: false });
}

export function updateProfile(data: UserUpdate): Promise<{ user: User }> {
  return put<{ user: User }>("/auth/me", data);
}
```

> 注意：`request.ts` 的 `put` 已存在（第 144-147 行）。

#### 3.2.3 修复登录时序（`miniapp/src/stores/auth.ts`）—— 核心

后端已直接返回 user，`login()` 改为**单次请求即完成持久化**，消除「先 getMe 再 setAuth」竞态：

```ts
async login() {
  const code = await getLoginCode();
  const result = await loginApi({ code });
  // 后端已返回 user，直接持久化，避免「先 getMe 再 setAuth」的未登录短路
  this.setAuth(result.access_token, result.user);
  return result.user;
}
```

同时新增 `updateUser(user)` action 用于资料编辑后刷新本地 user 缓存：

```ts
/** 资料更新后同步本地缓存 */
updateUser(user: User) {
  this.user = user;
  uni.setStorageSync(USER_KEY, JSON.stringify(user));
}
```

> `getMe` 服务函数保留（`GET /auth/me` 仍可用于刷新资料），但 `login()` 不再依赖它。

#### 3.2.4 「我的」页（`miniapp/src/pages/mine/mine.vue`）

参考 tarot `profile.vue` 布局，已登录时用户信息卡**可点击**进入编辑页（右侧 `›` 箭头）：

- 头像 + 昵称 + **脱敏 uid**（工具 `maskMiddle(id, 4)`，如 `ID 1***2`）
- 次级行展示 `性别 · 生日`（如 `男 · 生日 2000-06-15`）
- 未登录显示「微信一键登录」；已登录显示「编辑资料」「退出登录」
- 头像缺失用 emoji 🎾 兜底

**uid 脱敏工具**（`miniapp/src/utils/` 新增）：

```ts
export function maskMiddle(value: string | number, keep = 4): string {
  const s = String(value);
  if (s.length <= keep * 2) return "***";
  return `${s.slice(0, keep)}***${s.slice(-keep)}`;
}
```

**头像 URL 解析**（`miniapp/src/utils/` 新增 `resolveUploadUrl`）：把后端相对路径 `avatars/<user_id>/<uuid>.<ext>` 拼为完整可展示 URL。

#### 3.2.5 新增资料编辑页（`miniapp/src/pages/profile-edit/profile-edit.vue`）

参考 tarot `profile-detail.vue`，落地 Tailwind 自定义组件样式（表单一列为「左标签 + 右值/输入」）：

- **头像**：小程序 `<button open-type="chooseAvatar" @chooseavatar>`，`uni.uploadFile` 上传到 `/api/upload/avatar`，拿到 url 后 `updateProfile({ avatar_url })`
- **昵称**：`<input type="nickname">`
- **性别**：`<picker>`（保密/男/女），保存时 `updateProfile({ gender })`
- **生日**：`<picker mode="date">`，保存时 `updateProfile({ birthday })`
- 保存按钮统一提交昵称/性别/生日；头像变更即时保存
- 保存后调用 `authStore.updateUser(result.user)` 刷新缓存，`uni.navigateBack()` 返回
- 未登录时 `onShow` 校验 `isLoggedIn`，否则提示

**页面注册**：在 `miniapp/src/pages.json` 添加 `pages/profile-edit/profile-edit`。

## 四、TDD 测试方案

### 4.1 后端测试（`server/tests/`）

| 测试文件 | 用例 |
|---|---|
| `tests/routers/test_auth.py`（补充） | 登录返回 `user` + `is_new`；`TestUpdateMe`：更新昵称 / 部分更新不覆盖 / 更新性别生日 / 性别越界 422 / 未登录 401 |
| `tests/routers/test_upload.py`（新增） | `TestUploadAvatar`（成功/非法扩展名 400/未登录）+ `TestDownloadAvatar`（下载自己/越权 404/未登录） |

### 4.2 前端（`miniapp/`）

- `stores/auth.test.ts`（新增，如已配 vitest）：`login` 一次调用即 `setAuth`、`token`/`user` 写入 storage
- `utils/mask.test.ts`：`maskMiddle` 脱敏正确性

## 五、验收标准

1. 点击「微信一键登录」后**不再**提示「请先登录」，登录成功进入已登录态，头像/昵称/uid 正确展示。
2. `POST /api/auth/login` 返回体含 `access_token`、`user`、`is_new`。
3. `PUT /api/auth/me` 能更新昵称、头像、性别、生日，且只更新传入字段。
4. `POST /api/upload/avatar` 能上传头像，返回可访问 URL，前端可正常 `<image>` 展示。
5. 「我的」页展示脱敏 uid + 性别/生日；「编辑资料」页可改昵称/换头像/选性别/选生日，保存后本地缓存同步。
6. `cd server && bash scripts/verify.sh`（ruff + pytest）全部通过；前端 `type-check` 与 `build:mp-weixin` 通过。
7. 登出后 uid/昵称不残留（storage 清理正确）。

## 六、可选增强（本次不强制）

| 增强项 | 说明 | 是否纳入 |
|---|---|---|
| `gender` / `birthday` 字段 | User 模型加列 + schema + 编辑页 picker | ✅ 已纳入（对齐 tarot UserInfo） |
| `email` 绑定 | tarot 有邮箱绑定，网球日记无跨端同步强需求 | 未纳入 |
| 新用户引导 | 首次登录 `is_new` 时跳转资料完善页 | 可选 |
| 头像下载 | 采用独立 `upload.py` 的 `GET /upload/avatar/{user_id}/{filename}`（含越权校验），无需改 `files.py` | ✅ 已实现 |

## 七、风险与注意事项

- **`server/app/core/config.py` 绝对路径**：改动 `upload.py` 时勿动 `config.py` 的 `load_dotenv` 层级（向上三级到 `server/.env`），否则 `WX_APPID` 等读不到。
- **头像归属校验**：头像通过独立 `upload.py` 的 `GET /upload/avatar/{user_id}/{filename}` 下载，仅允许 `user_id == 当前用户`；`files.py` 的 `_is_file_owned` 保持只认 `Gear.photo`，两者互不干扰。
- **`request.ts` 门控**：`login()` 修复后不再走 `getMe()`，但仍保留门控作为其他业务页的兜底，勿删除。
- **compat**：`getMe` 服务与 `Token` 类型保留（`Token` 仍被 `LoginResponse` 继承），避免破坏其他引用。
- **gender 取值**：与 tarot 一致用数字 index（0=保密 1=男 2=女），schema 校验 `ge=0, le=2`。

## 八、实施步骤

1. **后端 Schemas**：`schemas.py` 新增 `UserUpdate`、`LoginResponse`、`UserUpdateResponse`
2. **后端登录改造**：`auth.py` 的 `login` 返回 `LoginResponse`
3. **后端资料更新**：`auth.py` 新增 `PUT /me`
4. **后端头像上传**：新建 `upload.py` + `main.py` 注册 + `files.py` 归属扩展
5. **后端测试**：补齐 `test_auth.py`、新增 `test_upload.py`，跑 `verify.sh`
6. **前端类型**：`types/index.ts` 加 `LoginResponse`/`UserUpdate`
7. **前端服务层**：`services/auth.ts` 改 `login` 返回类型、加 `updateProfile`/`uploadAvatar`
8. **前端登录修复**：`stores/auth.ts` 改 `login()` + 加 `updateUser`
9. **前端工具**：`utils/mask.ts`（`maskMiddle`）
10. **前端页面**：改 `mine.vue`（uid/编辑入口）+ 新建 `profile-edit.vue` + `pages.json` 注册
11. **联调验证**：一键登录 → 资料编辑 → 登出全流程
12. **更新状态**：本方案文档标记 ✅ 已完成
