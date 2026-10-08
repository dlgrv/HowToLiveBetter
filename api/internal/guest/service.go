package guest

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
)

var (
	ErrInvalidClaim = errors.New("invalid or expired claim code")
	ErrClaimUsed    = errors.New("claim code already used")
)

type Service struct {
	App      core.App
	GuestTTL time.Duration
	ClaimTTL time.Duration
}

func (s Service) CreateSession() (token string, expiresAt time.Time, err error) {
	token, err = randomToken(32)
	if err != nil {
		return "", time.Time{}, err
	}
	col, err := s.App.FindCollectionByNameOrId("guest_sessions")
	if err != nil {
		return "", time.Time{}, err
	}
	expiresAt = time.Now().Add(s.GuestTTL)
	rec := core.NewRecord(col)
	rec.Set("tokenHash", authz.HashToken(token))
	rec.Set("status", "active")
	dt, err := types.ParseDateTime(expiresAt)
	if err != nil {
		return "", time.Time{}, err
	}
	rec.Set("expiresAt", dt)
	if err := s.App.Save(rec); err != nil {
		return "", time.Time{}, err
	}
	return token, expiresAt, nil
}

func (s Service) CreateClaimCode(guestID string) (code string, expiresAt time.Time, err error) {
	code, err = randomToken(18)
	if err != nil {
		return "", time.Time{}, err
	}
	col, err := s.App.FindCollectionByNameOrId("guest_claims")
	if err != nil {
		return "", time.Time{}, err
	}
	expiresAt = time.Now().Add(s.ClaimTTL)
	rec := core.NewRecord(col)
	rec.Set("codeHash", authz.HashToken(code))
	rec.Set("guestId", guestID)
	rec.Set("status", "pending")
	dt, _ := types.ParseDateTime(expiresAt)
	rec.Set("expiresAt", dt)
	if err := s.App.Save(rec); err != nil {
		return "", time.Time{}, err
	}
	return code, expiresAt, nil
}

func (s Service) Claim(code string) (token string, expiresAt time.Time, err error) {
	hash := authz.HashToken(code)
	claim, err := s.App.FindFirstRecordByFilter(
		"guest_claims",
		"codeHash = {:h}",
		dbx.Params{"h": hash},
	)
	if err != nil {
		return "", time.Time{}, ErrInvalidClaim
	}
	if claim.GetString("status") != "pending" {
		return "", time.Time{}, ErrClaimUsed
	}
	exp := claim.GetDateTime("expiresAt").Time()
	if time.Now().After(exp) {
		return "", time.Time{}, ErrInvalidClaim
	}
	guestID := claim.GetString("guestId")
	guest, err := s.App.FindRecordById("guest_sessions", guestID)
	if err != nil {
		return "", time.Time{}, ErrInvalidClaim
	}
	if guest.GetString("status") != "active" {
		return "", time.Time{}, ErrInvalidClaim
	}
	// Issue a fresh long-lived token (rotate) bound to same guest session id
	token, err = randomToken(32)
	if err != nil {
		return "", time.Time{}, err
	}
	expiresAt = time.Now().Add(s.GuestTTL)
	err = s.App.RunInTransaction(func(txApp core.App) error {
		g, err := txApp.FindRecordById("guest_sessions", guestID)
		if err != nil {
			return err
		}
		g.Set("tokenHash", authz.HashToken(token))
		dt, _ := types.ParseDateTime(expiresAt)
		g.Set("expiresAt", dt)
		if err := txApp.Save(g); err != nil {
			return err
		}
		c, err := txApp.FindRecordById("guest_claims", claim.Id)
		if err != nil {
			return err
		}
		c.Set("status", "used")
		return txApp.Save(c)
	})
	if err != nil {
		return "", time.Time{}, fmt.Errorf("claim: %w", err)
	}
	return token, expiresAt, nil
}

func randomToken(n int) (string, error) {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

// HashClaim is exported for tests.
func HashClaim(code string) string {
	sum := sha256.Sum256([]byte(code))
	return hex.EncodeToString(sum[:])
}
