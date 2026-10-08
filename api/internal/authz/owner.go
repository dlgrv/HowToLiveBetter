package authz

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"errors"
	"strings"
	"time"

	"github.com/pocketbase/dbx"

	"github.com/pocketbase/pocketbase/core"
)

const HeaderSync = "X-HTLB-Sync"

var (
	ErrUnauthorized = errors.New("unauthorized")
	ErrForbidden    = errors.New("forbidden")
)

type Kind string

const (
	KindGuest Kind = "guest"
	KindUser  Kind = "user"
)

type Owner struct {
	Kind Kind
	ID   string
}

type Resolver struct {
	App core.App
}

func HashToken(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}

func (r Resolver) Resolve(e *core.RequestEvent) (Owner, error) {
	if e.Auth != nil {
		return Owner{Kind: KindUser, ID: e.Auth.Id}, nil
	}
	raw := strings.TrimSpace(e.Request.Header.Get(HeaderSync))
	if raw == "" {
		return Owner{}, ErrUnauthorized
	}
	hash := HashToken(raw)
	rec, err := r.App.FindFirstRecordByFilter(
		"guest_sessions",
		"tokenHash = {:h} && status = 'active'",
		dbx.Params{"h": hash},
	)
	if err != nil {
		return Owner{}, ErrUnauthorized
	}
	exp := rec.GetDateTime("expiresAt").Time()
	if !exp.IsZero() && time.Now().After(exp) {
		return Owner{}, ErrUnauthorized
	}
	stored := rec.GetString("tokenHash")
	if subtle.ConstantTimeCompare([]byte(stored), []byte(hash)) != 1 {
		return Owner{}, ErrUnauthorized
	}
	return Owner{Kind: KindGuest, ID: rec.Id}, nil
}

func (r Resolver) ResolveOptional(e *core.RequestEvent) (Owner, bool) {
	o, err := r.Resolve(e)
	if err != nil {
		return Owner{}, false
	}
	return o, true
}
