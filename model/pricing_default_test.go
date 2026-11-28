package model

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDefaultVendorsRecognizeProviderModelAliases(t *testing.T) {
	for name, want := range map[string]string{
		"google/nano-banana": "Google", "nano-banana-2": "Google", "nano-banana-pro": "Google",
		"nano-banana-2-1": "Google", "nano-banana-2-lite": "Google", "google/imagen4": "Google",
		"google/imagen4-fast": "Google", "google/imagen4-ultra": "Google", "veo3_fast": "Google",
		"o4-mini": "OpenAI", "gpt-image-2": "OpenAI", "bytedance/seedream-v4": "字节跳动",
		"seedance-2": "字节跳动", "flux-2/pro-text-to-image": "Black Forest Labs",
		"wan/2-6-text-to-video": "阿里巴巴", "hailuo-2.3": "MiniMax",
	} {
		t.Run(name, func(t *testing.T) {
			metadata := map[string]*Model{}
			vendors := map[int]*Vendor{}
			initDefaultVendorMapping(metadata, vendors, []AbilityWithChannel{{Ability: Ability{Model: name}}})
			require.NotNil(t, metadata[name])
			vendor := vendors[metadata[name].VendorID]
			require.NotNil(t, vendor)
			assert.Equal(t, want, vendor.Name)
			assert.Negative(t, vendor.Id)
		})
	}
}

func TestDefaultVendorFillsIncompleteMetadataWithoutMutatingSharedRules(t *testing.T) {
	rule := &Model{Id: 10, ModelName: "image", NameRule: NameRuleContains, Description: "Retain description", Status: 0}
	metadata := map[string]*Model{"google/imagen4": rule, "gpt-image-2": rule}
	vendors := map[int]*Vendor{7: {Id: 7, Name: "Google"}}
	initDefaultVendorMapping(metadata, vendors, []AbilityWithChannel{{Ability: Ability{Model: "google/imagen4"}}, {Ability: Ability{Model: "gpt-image-2"}}})
	assert.Zero(t, rule.VendorID)
	assert.Equal(t, 7, metadata["google/imagen4"].VendorID)
	assert.Equal(t, "OpenAI", vendors[metadata["gpt-image-2"].VendorID].Name)
	assert.Equal(t, "Retain description", metadata["google/imagen4"].Description)
	assert.Zero(t, metadata["google/imagen4"].Status)
}

func TestDefaultVendorPreservesExplicitVendorAndRepairsDanglingReference(t *testing.T) {
	explicit := &Model{ModelName: "nano-banana-pro", VendorID: 8}
	metadata := map[string]*Model{"nano-banana-pro": explicit, "o4-mini": {ModelName: "o4-mini", VendorID: 99}}
	vendors := map[int]*Vendor{8: {Id: 8, Name: "Custom vendor"}}
	initDefaultVendorMapping(metadata, vendors, []AbilityWithChannel{{Ability: Ability{Model: "nano-banana-pro"}}, {Ability: Ability{Model: "o4-mini"}}})
	assert.Same(t, explicit, metadata["nano-banana-pro"])
	assert.Equal(t, "OpenAI", vendors[metadata["o4-mini"].VendorID].Name)
}
