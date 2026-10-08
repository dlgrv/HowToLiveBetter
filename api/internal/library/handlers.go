package library

import (
	"net/http"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/router"
)

type Handlers struct {
	Svc Service
	Az  authz.Resolver
}

func Register(g *router.RouterGroup[*core.RequestEvent], h Handlers) {
	g.GET("/bookmarks", h.listBookmarks)
	g.PUT("/bookmarks", h.putBookmark)
	g.DELETE("/bookmarks", h.deleteBookmark)
	g.GET("/reading", h.getReading)
	g.PUT("/reading", h.putReading)
}

func (h Handlers) requireOwner(e *core.RequestEvent) (authz.Owner, error) {
	owner, err := h.Az.Resolve(e)
	if err != nil {
		return owner, e.UnauthorizedError("credential required", nil)
	}
	return owner, nil
}

func (h Handlers) listBookmarks(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	items, err := h.Svc.ListBookmarks(owner)
	if err != nil {
		return e.InternalServerError("list failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"items": items})
}

func (h Handlers) putBookmark(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	var body struct {
		EntryID string `json:"entryId"`
		Note    string `json:"note"`
	}
	if err := e.BindBody(&body); err != nil || body.EntryID == "" {
		return e.BadRequestError("entryId required", nil)
	}
	if err := h.Svc.UpsertBookmark(owner, body.EntryID, body.Note); err != nil {
		return e.InternalServerError("save failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"ok": true})
}

func (h Handlers) deleteBookmark(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	entryID := e.Request.URL.Query().Get("entryId")
	if entryID == "" {
		return e.BadRequestError("entryId required", nil)
	}
	if err := h.Svc.DeleteBookmark(owner, entryID); err != nil {
		return e.InternalServerError("delete failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"ok": true})
}

func (h Handlers) getReading(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	r, err := h.Svc.GetReading(owner)
	if err != nil {
		return e.InternalServerError("get failed", err)
	}
	return e.JSON(http.StatusOK, r)
}

func (h Handlers) putReading(e *core.RequestEvent) error {
	owner, err := h.requireOwner(e)
	if err != nil {
		return err
	}
	var body Reading
	if err := e.BindBody(&body); err != nil || body.Chapter == "" {
		return e.BadRequestError("chapter required", nil)
	}
	if err := h.Svc.PutReading(owner, body.Chapter, body.Offset); err != nil {
		return e.InternalServerError("save failed", err)
	}
	return e.JSON(http.StatusOK, map[string]any{"ok": true})
}
