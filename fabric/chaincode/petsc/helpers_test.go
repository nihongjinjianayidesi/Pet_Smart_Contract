package main

import "testing"

func TestSha256Hex(t *testing.T) {
	got := sha256Hex("hello")
	if len(got) != 64 {
		t.Fatalf("expected 64 hex chars, got %d (%s)", len(got), got)
	}
	if !isSHA256Hex(got) {
		t.Fatalf("expected isSHA256Hex true, got false (%s)", got)
	}
}

func TestRound2(t *testing.T) {
	if v := round2(1.005); v != 1.0 {
		t.Fatalf("expected 1.0, got %v", v)
	}
	if v := round2(1.006); v != 1.01 {
		t.Fatalf("expected 1.01, got %v", v)
	}
}

