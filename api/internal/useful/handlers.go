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
	g.GET("/useful", h.get)
	g.POST("/useful", h.post)
}

func (h Handlers) get(e *core.RequestEvent) error {
	ids := e.Request.URL.Query().Get("entryIds")
	if ids == "" {
		ids = e.Request.URL.Query().Get("entryId")
	}
	parts := splitIDs(ids)
	if len(parts) == 0 {
		return e.BadRequestError("entryId or entryIds required", nil)
	}
	owner, ok := h.Az.ResolveOptional(e)
	counts, err := h.Svc.Counts(parts)
	if err != nil {
		return e.InternalServerError("count failed", err)
	}
	items := make([]map[string]any, 0, len(parts))
	for _, id := range parts {
		item := map[string]any{"entryId": id, "count": counts[id]}
		if ok {
			v, err := h.Svc.Get(owner, id)
			if err == nil {
				item["useful"] = v.Useful
			}
		}
		items = append(items, item)
	}
	return e.JSON(http.StatusOK, map[string]any{"items": items})
}

func (h Handlers) post(e *core.RequestEvent) error {
	owner, err := h.Az.Resolve(e)
	if err != nil {
		return e.UnauthorizedError("credential required", nil)
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
