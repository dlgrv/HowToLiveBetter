package useful

import (
	"net/http"
	"strings"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type Handlers struct {
	Svc Service
	Az  authz.Resolver
}

func Register(g *router.RouterGroup[*core.RequestEvent], h Handlers) {
	g.GET("/useful/mine", h.Mine)
	g.GET("/useful", h.Get)
	g.POST("/useful", h.Post)
}

func (h Handlers) Mine(e *core.RequestEvent) error {
	owner, err := h.Az.Resolve(e)
	if err != nil {
		return e.UnauthorizedError("credential required", nil)
	}
	if owner.Kind != authz.KindUser {
		return e.UnauthorizedError("sign-in required", nil)
	}
	ids, err := h.Svc.ListMine(owner)
	if err != nil {
		return e.InternalServerError("list failed", err)
	}
	items := make([]map[string]any, 0, len(ids))
	for _, id := range ids {
		items = append(items, map[string]any{"entryId": id})
	}
	return e.JSON(http.StatusOK, map[string]any{"items": items})
}

func (h Handlers) Get(e *core.RequestEvent) error {
	ids := e.Request.URL.Query().Get("entryIds")
	if ids == "" {
		ids = e.Request.URL.Query().Get("entryId")
	}
	parts := splitIDs(ids)
	if len(parts) == 0 {
		return e.BadRequestError("entryId or entryIds required", nil)
	}
	owner, ok := h.Az.ResolveOptional(e)
	userOK := ok && owner.Kind == authz.KindUser
	counts, err := h.Svc.Counts(parts)
	if err != nil {
		return e.InternalServerError("count failed", err)
	}
	items := make([]map[string]any, 0, len(parts))
	for _, id := range parts {
		item := map[string]any{"entryId": id, "count": counts[id]}
		if userOK {
			v, err := h.Svc.Get(owner, id)
			if err == nil {
				item["useful"] = v.Useful
			}
		}
		items = append(items, item)
	}
	return e.JSON(http.StatusOK, map[string]any{"items": items})
}

func (h Handlers) Post(e *core.RequestEvent) error {
	owner, err := h.Az.Resolve(e)
	if err != nil {
		return e.UnauthorizedError("credential required", nil)
	}
	if owner.Kind != authz.KindUser {
		return e.UnauthorizedError("sign-in required", nil)
	}
	var body struct {
		EntryID string `json:"entryId"`
		Useful  *bool  `json:"useful"`
	}
	if err := e.BindBody(&body); err != nil || body.EntryID == "" || body.Useful == nil {
		return e.BadRequestError("entryId and useful required", nil)
	}
	res, err := h.Svc.Toggle(owner, body.EntryID, *body.Useful)
	if err != nil {
		return e.InternalServerError("vote failed", err)
	}
	return e.JSON(http.StatusOK, res)
}

func splitIDs(s string) []string {
	var out []string
	for _, p := range strings.Split(s, ",") {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}
