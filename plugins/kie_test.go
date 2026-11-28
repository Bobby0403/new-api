package plugins_test

import (
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"testing"

	"github.com/QuantumNous/new-api/common"
	"github.com/QuantumNous/new-api/constant"
	"github.com/QuantumNous/new-api/model"
	"github.com/QuantumNous/new-api/pkg/jsplugin"
	builtinplugins "github.com/QuantumNous/new-api/plugins"
	"github.com/QuantumNous/new-api/relay"
	"github.com/QuantumNous/new-api/relay/channel"
	taskplugin "github.com/QuantumNous/new-api/relay/channel/task/jsplugin"
	relaycommon "github.com/QuantumNous/new-api/relay/common"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newKiePlugin(t *testing.T) *jsplugin.LoadedPlugin {
	t.Helper()
	source, err := builtinplugins.Source("kie")
	require.NoError(t, err)
	plugin, err := jsplugin.NewRegistry().RegisterFactory(source, jsplugin.Options{Key: "kie"})
	require.NoError(t, err)
	return plugin
}

func callKie(t *testing.T, plugin *jsplugin.LoadedPlugin, export string, path []string, args ...any) map[string]any {
	t.Helper()
	value, err := plugin.Engine.CallPath(t.Context(), export, path, args...)
	require.NoError(t, err)
	return decodePluginValue(t, value)
}

func TestKieProtocolInputsAndBilling(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, tc := range []struct {
		name, protocol, model, action, operation, vendorModel string
		body, wantInput, wantFacts                            map[string]any
	}{
		{name: "GPT Image text generation", protocol: "openai_image", model: "gpt-image-1.5", action: "image", operation: "generate", vendorModel: "gpt-image/1.5-text-to-image",
			body:      map[string]any{"prompt": "a blue test image", "size": "1024x1024"},
			wantInput: map[string]any{"prompt": "a blue test image", "aspect_ratio": "1:1", "quality": "medium"},
			wantFacts: map[string]any{"requests": float64(1), "image_count": float64(1), "quality": "medium"}},
		{name: "GPT Image edits", protocol: "openai_image", model: "gpt-image-1.5", action: "image", operation: "edit", vendorModel: "gpt-image/1.5-image-to-image",
			body:      map[string]any{"prompt": "make it blue", "image": "https://cdn.example/input.png", "quality": "high"},
			wantInput: map[string]any{"prompt": "make it blue", "input_urls": []any{"https://cdn.example/input.png"}, "aspect_ratio": "1:1", "quality": "high"},
			wantFacts: map[string]any{"requests": float64(1), "image_count": float64(1), "quality": "high"}},
		{name: "image count and explicit zero", protocol: "openai_image", model: "bytedance/seedream-v4-text-to-image", action: "image",
			body:      map[string]any{"prompt": "three cats", "n": 3, "metadata": map[string]any{"seed": 0, "nsfw_checker": false}},
			wantInput: map[string]any{"prompt": "three cats", "max_images": float64(3), "seed": float64(0), "nsfw_checker": false, "image_size": "square_hd", "image_resolution": "1K"},
			wantFacts: map[string]any{"requests": float64(1), "image_count": float64(3), "image_resolution": "1K"}},
		{name: "nano banana edit", protocol: "openai_image", model: "nano-banana-pro", action: "image",
			body:      map[string]any{"prompt": "make it blue", "image": "https://cdn.example/input.jpg", "resolution": "4K"},
			wantInput: map[string]any{"prompt": "make it blue", "image_input": []any{"https://cdn.example/input.jpg"}, "resolution": "4K", "aspect_ratio": "1:1"},
			wantFacts: map[string]any{"requests": float64(1), "image_count": float64(1), "resolution": "4K"}},
		{name: "video seconds override metadata", protocol: "openai_video", model: "kling-2.6/text-to-video", action: "video",
			body:      map[string]any{"prompt": "a cat walks", "seconds": 5, "sound": false, "metadata": map[string]any{"duration": "10", "sound": true}},
			wantInput: map[string]any{"prompt": "a cat walks", "duration": "5", "sound": false, "aspect_ratio": "1:1"},
			wantFacts: map[string]any{"requests": float64(1), "seconds": float64(5), "sound": false}},
		{name: "Responses image reference", protocol: "openai_responses", model: "wan/2-6-image-to-video", action: "video",
			body:      map[string]any{"input": []any{map[string]any{"role": "user", "content": []any{map[string]any{"type": "input_text", "text": "animate this"}, map[string]any{"type": "input_image", "image_url": "https://cdn.example/frame.png"}}}}, "metadata": map[string]any{"duration": "15", "resolution": "720p"}},
			wantInput: map[string]any{"prompt": "animate this", "image_urls": []any{"https://cdn.example/frame.png"}, "duration": "15", "resolution": "720p", "multi_shots": false},
			wantFacts: map[string]any{"requests": float64(1), "seconds": float64(15), "resolution": "720p"}},
		{name: "native quality via Responses", protocol: "openai_responses", model: "seedream/4.5-text-to-image", action: "image",
			body:      map[string]any{"input": "a landscape", "metadata": map[string]any{"quality": "high", "aspect_ratio": "16:9"}},
			wantInput: map[string]any{"prompt": "a landscape", "quality": "high", "aspect_ratio": "16:9"},
			wantFacts: map[string]any{"requests": float64(1), "image_count": float64(1), "quality": "high"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			body := map[string]any{}
			for k, v := range tc.body {
				body[k] = v
			}
			body["model"] = tc.model
			intent := callKie(t, plugin, "protocols", []string{tc.protocol, "decodeRequest"}, map[string]any{"model": tc.model, "operation": tc.operation, "body": map[string]any{"kind": "json", "value": body}})
			assert.Equal(t, tc.action, intent["action"])
			request := intent["requestBody"].(map[string]any)
			assert.Equal(t, tc.wantInput, request["input"])
			ctx := map[string]any{"model": tc.model, "upstreamModel": tc.model, "baseUrl": "https://api.kie.example/", "apiKey": "test-key", "requestBody": request}
			descriptor := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
			assert.Equal(t, "https://api.kie.example/api/v1/jobs/createTask", descriptor["url"])
			wantVendor := tc.vendorModel
			if wantVendor == "" {
				wantVendor = tc.model
			}
			assert.Equal(t, map[string]any{"model": wantVendor, "input": tc.wantInput}, descriptor["body"])
			assert.Equal(t, "Bearer test-key", descriptor["headers"].(map[string]any)["Authorization"])
			facts := callKie(t, plugin, "extractUsage", nil, ctx)
			assert.Equal(t, tc.wantFacts, facts)
			schema, _ := plugin.Meta.UsageForModel(tc.model)
			require.Len(t, facts, len(schema))
			for key := range facts {
				assert.Contains(t, schema, key)
			}
		})
	}
}

func TestKieRejectsInvalidQuantitiesBeforeSubmission(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, tc := range []struct {
		name, model string
		body        map[string]any
		want        string
	}{
		{"GPT 2 resolution ratio", "gpt-image-2-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"resolution": "2K", "aspect_ratio": "5:4"}}, "Unsupported aspect ratio"},
		{"GPT 2.5 resolution ratio", "gpt-image-2-5-flare-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"resolution": "4K", "aspect_ratio": "27:16"}}, "Unsupported aspect ratio"},
		{"GPT 2 background restriction", "gpt-image-2-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"resolution": "2K", "background": "transparent"}}, "background is supported only at 1K"},
		{"GPT 2.6 GIF frame bound", "gpt-image-2-6/flare-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"output_format": "gif", "frame_count": 17}}, "frame_count"},
		{"GPT 2.6 GIF pixel bound", "gpt-image-2-6/flare-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"output_format": "gif", "size": "1024x1024"}}, "sprite sheet"},
		{"GPT 2.6 compression bound", "gpt-image-2-6/sunburst-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"output_format": "webp", "output_compression": 101}}, "output_compression"},
		{"GPT 2.6 GIF duration bound", "gpt-image-2-6/flare-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"output_format": "gif", "frame_duration_ms": 0}}, "frame_duration_ms"},
		{"GPT 2.6 SVG author", "gpt-image-2-6/sunburst-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"output_format": "svg", "svg": map[string]any{"model": "unknown"}}}, "Unsupported SVG author"},
		{"GPT 2.6 edit URL bound", "gpt-image-2-6/flare-image-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"input_urls": slices.Repeat([]any{"https://cdn.example/a.png"}, 17)}}, "HTTP URLs"},
		{"negative metadata duration", "grok-imagine/text-to-video", map[string]any{"prompt": "p", "metadata": map[string]any{"duration": -1}}, "duration"},
		{"overflow seconds", "grok-imagine/text-to-video", map[string]any{"prompt": "p", "seconds": 1e30}, "supported range"},
		{"fractional seconds", "grok-imagine/text-to-video", map[string]any{"prompt": "p", "seconds": 6.5}, "supported range"},
		{"vendor enum duration", "kling-2.6/text-to-video", map[string]any{"prompt": "p", "seconds": 7}, "Unsupported input.duration"},
		{"metadata count bypass", "bytedance/seedream-v4-text-to-image", map[string]any{"prompt": "p", "metadata": map[string]any{"max_images": 129}}, "max_images"},
		{"zero count", "bytedance/seedream-v4-text-to-image", map[string]any{"prompt": "p", "n": 0}, "image count"},
		{"unsupported multiple images", "nano-banana-pro", map[string]any{"prompt": "p", "n": 2}, "image count"},
		{"undeclared billing passthrough", "nano-banana-pro", map[string]any{"prompt": "p", "metadata": map[string]any{"n": 129}}, "Unsupported Kie input field"},
		{"metadata cannot replace model", "nano-banana-pro", map[string]any{"prompt": "p", "metadata": map[string]any{"model": "other"}}, "Unsupported Kie input field"},
		{"invalid boolean", "kling-2.6/text-to-video", map[string]any{"prompt": "p", "sound": "false"}, "must be a boolean"},
		{"inline image unsupported", "nano-banana-pro", map[string]any{"prompt": "p", "image": "data:image/png;base64,AA=="}, "HTTP URLs"},
		{"image model cannot take seconds", "nano-banana-pro", map[string]any{"prompt": "p", "seconds": 10}, "Unsupported Kie input field"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, err := plugin.Engine.CallPath(t.Context(), "protocols", []string{"openai_responses", "decodeRequest"}, map[string]any{"model": tc.model, "body": map[string]any{"kind": "json", "value": tc.body}})
			require.ErrorContains(t, err, tc.want)
		})
	}
	// Native and driver paths revalidate independently of the host protocol.
	for _, hook := range []string{"buildSubmitRequest", "extractUsage"} {
		_, err := plugin.Engine.Call(t.Context(), hook, map[string]any{"model": "bytedance/seedream-v4-text-to-image", "baseUrl": "https://api.kie.example", "requestBody": map[string]any{"input": map[string]any{"prompt": "p", "max_images": 129}}})
		require.ErrorContains(t, err, "max_images", hook)
	}
	_, err := plugin.Engine.CallPath(t.Context(), "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": map[string]any{"model": "grok-imagine/text-to-video", "input": map[string]any{"prompt": "p", "duration": 31}}}})
	require.ErrorContains(t, err, "supported range")
}

func TestKiePollingAndActualImageUsage(t *testing.T) {
	plugin := newKiePlugin(t)
	adaptor := taskplugin.New(plugin)
	adaptor.Init(&relaycommon.RelayInfo{ChannelMeta: &relaycommon.ChannelMeta{ChannelBaseUrl: "https://api.kie.example", ApiKey: "key"}})
	for _, tc := range []struct {
		name, state, result   string
		wantStatus, wantError string
		count                 float64
	}{
		{name: "waiting", state: "waiting", wantStatus: "NOT_START"},
		{name: "queued", state: "queuing", wantStatus: "QUEUED"},
		{name: "running", state: "generating", wantStatus: "IN_PROGRESS"},
		{name: "failed", state: "fail", wantStatus: "FAILURE"},
		{name: "unknown", state: "new-state", wantStatus: "UNKNOWN"},
		{name: "prototype key", state: "constructor", wantStatus: "UNKNOWN"},
		{name: "success", state: "success", result: `{"resultUrls":["https://cdn.example/a.png","https://cdn.example/b.png",""]}`, wantStatus: "SUCCESS", count: 2},
		{name: "payloadless success", state: "success", result: `{"resultUrls":[]}`, wantError: "without a valid media result"},
		{name: "invalid result JSON", state: "success", result: `{`, wantError: "JSON"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			body, err := common.Marshal(map[string]any{"code": 200, "data": map[string]any{"taskId": "private-id", "state": tc.state, "resultJson": tc.result, "failMsg": "provider failed", "costTime": 99}})
			require.NoError(t, err)
			task := &model.Task{TaskID: "public-id", Action: "image", Properties: model.Properties{OriginModelName: "bytedance/seedream-v4-text-to-image", UpstreamModelName: "bytedance/seedream-v4-text-to-image"}}
			result, err := adaptor.ParseTaskResult(task, &http.Response{StatusCode: 200}, body)
			if tc.wantError != "" {
				require.ErrorContains(t, err, tc.wantError)
				return
			}
			require.NoError(t, err)
			assert.Equal(t, tc.wantStatus, result.Status)
			if tc.count > 0 {
				assert.Equal(t, tc.count, result.UsageFacts["image_count"])
				assert.Equal(t, "https://cdn.example/a.png", result.Url)
			} else {
				assert.Empty(t, result.UsageFacts)
			}
			if tc.state == "fail" {
				assert.Equal(t, "provider failed", result.Reason)
			}
		})
	}
	for _, legacy := range []string{"gpt-image/1.5-image-to-image", "google/nano-banana-edit"} {
		task := &model.Task{TaskID: "legacy-task", Action: "image", Properties: model.Properties{OriginModelName: legacy, UpstreamModelName: legacy}}
		body := []byte(`{"code":200,"data":{"state":"success","response":{"resultUrls":["https://cdn.example/legacy.png"]}}}`)
		completed, err := adaptor.ParseTaskResult(task, &http.Response{StatusCode: http.StatusOK}, body)
		require.NoError(t, err)
		assert.Equal(t, float64(1), completed.UsageFacts["image_count"])
	}
	// HTTP 200 with a vendor error code must fail, never become a pending task.
	for _, code := range []int{401, 429, 500} {
		_, err := plugin.Engine.Call(t.Context(), "parseSubmitResponse", map[string]any{}, map[string]any{"body": map[string]any{"code": code, "msg": "upstream error"}})
		require.ErrorContains(t, err, "upstream error")
		_, err = plugin.Engine.Call(t.Context(), "parseTaskResult", map[string]any{}, map[string]any{"code": code, "msg": "poll error"})
		require.ErrorContains(t, err, "poll error")
	}
	value, err := plugin.Engine.Call(t.Context(), "extractUsageOnComplete", map[string]any{"model": "wan/2-6-text-to-video"}, map[string]any{}, map[string]any{"code": 200, "data": map[string]any{"state": "success", "costTime": 999, "creditsConsumed": 999}})
	require.NoError(t, err)
	assert.Nil(t, value, "processing latency and vendor credits must not become output seconds")
}

func TestKieGatewayRoundTripAndArtifacts(t *testing.T) {
	plugin := newKiePlugin(t)
	const modelName = "nano-banana-pro"
	gateway := map[string]any{"kind": "new_api"}
	ctx := map[string]any{"model": "my-image-alias", "upstreamModel": modelName, "baseUrl": "https://gateway.example", "apiKey": "gateway-token", "upstream": gateway, "requestBody": map[string]any{"input": map[string]any{"prompt": "p", "resolution": "2K"}}}
	sent := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
	assert.Equal(t, "https://gateway.example/kie/api/v1/jobs/createTask", sent["url"])
	assert.Equal(t, modelName, sent["body"].(map[string]any)["model"])
	intent := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": sent["body"]}})
	assert.Equal(t, modelName, intent["model"])
	upstream := map[string]any{"model": modelName, "upstreamModel": modelName, "baseUrl": "https://api.kie.example", "apiKey": "vendor-key", "authHeader": "vendor-key", "requestBody": intent["requestBody"]}
	forwarded := callKie(t, plugin, "buildSubmitRequest", nil, upstream)
	assert.Equal(t, sent["body"], forwarded["body"])
	assert.Equal(t, "Bearer vendor-key", forwarded["headers"].(map[string]any)["Authorization"])
	assert.Equal(t, callKie(t, plugin, "extractUsage", nil, ctx), callKie(t, plugin, "extractUsage", nil, upstream))
	created := callKie(t, plugin, "native", []string{"taskCreated"}, map[string]any{}, map[string]any{"task_id": "public-id"})
	submitted := callKie(t, plugin, "parseSubmitResponse", nil, ctx, map[string]any{"body": created})
	assert.Equal(t, "public-id", submitted["taskId"])
	query := callKie(t, plugin, "buildQueryRequest", nil, map[string]any{"baseUrl": "https://gateway.example", "apiKey": "gateway-token", "authHeader": "Bearer gateway-token", "upstream": gateway, "taskId": "public id/+"})
	assert.Equal(t, "https://gateway.example/kie/api/v1/jobs/recordInfo?taskId=public%20id%2F%2B", query["url"])
	assert.Equal(t, "Bearer gateway-token", query["headers"].(map[string]any)["Authorization"])
	vendorQuery := callKie(t, plugin, "buildQueryRequest", nil, map[string]any{"baseUrl": "https://api.kie.example", "apiKey": "vendor-key", "authHeader": "vendor-key", "taskId": "private-id"})
	assert.Equal(t, "Bearer vendor-key", vendorQuery["headers"].(map[string]any)["Authorization"])
	data := map[string]any{"code": 200, "data": map[string]any{"taskId": "private-id", "state": "success", "param": "private parameters", "resultJson": `{"resultUrls":["https://cdn.example/a.jpg","https://cdn.example/b.jpg"]}`}}
	status := callKie(t, plugin, "native", []string{"taskStatus"}, map[string]any{}, map[string]any{"task_id": "public-id", "status": "SUCCESS", "data": data})
	assert.Equal(t, "public-id", status["data"].(map[string]any)["taskId"])
	assert.NotContains(t, status["data"], "param")
	body, err := common.Marshal(data)
	require.NoError(t, err)
	adaptor := taskplugin.New(plugin)
	adaptor.Init(&relaycommon.RelayInfo{ChannelMeta: &relaycommon.ChannelMeta{ChannelBaseUrl: "https://api.kie.example", ApiKey: "vendor-key"}})
	task := &model.Task{TaskID: "public-id", Action: "image", Status: model.TaskStatusSuccess, Data: body}
	artifacts, err := adaptor.ListArtifacts(task)
	require.NoError(t, err)
	assert.Equal(t, []channel.TaskArtifact{{Key: "media_0", Type: "image"}, {Key: "media_1", Type: "image"}}, artifacts)
	content, err := adaptor.BuildContentRequest(t.Context(), task, "media_1", channel.TaskArtifactClientRequest{Method: http.MethodGet})
	require.NoError(t, err)
	assert.Equal(t, "https://cdn.example/b.jpg", content.URL)
	assert.Empty(t, content.Headers, "channel credentials must not reach the media CDN")
	_, err = adaptor.BuildContentRequest(t.Context(), task, "media_9", channel.TaskArtifactClientRequest{Method: http.MethodGet})
	require.Error(t, err)
	// Artifact contexts intentionally have no model; rendering uses their type.
	final := callKie(t, plugin, "protocols", []string{"openai_responses", "renderFinal"}, map[string]any{"artifacts": map[string]any{"media_0": map[string]any{"key": "media_0", "type": "image", "url": "https://gateway.example/signed-image"}}}, map[string]any{"status": "SUCCESS", "data": data})
	machine := relay.NewPluginResponsesMachine("public-id", modelName, 1, relay.DefaultPluginProtocolLimits())
	response, err := machine.FinalResponse(final, "SUCCESS")
	require.NoError(t, err)
	encoded, err := common.Marshal(response)
	require.NoError(t, err)
	assert.Contains(t, string(encoded), "gateway.example/signed-image")
	assert.NotContains(t, string(encoded), "cdn.example")
}

func TestKieReferencedTasksAndResponseForms(t *testing.T) {
	plugin := newKiePlugin(t)
	const videoModel = "grok-imagine/image-to-video"
	body := map[string]any{"model": videoModel, "input": map[string]any{"task_id": "public-origin", "index": 0, "duration": "10"}}
	intent := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": body}})
	assert.Equal(t, []any{"public-origin"}, intent["originTaskIds"])
	ctx := map[string]any{"model": videoModel, "baseUrl": "https://api.kie.example", "apiKey": "key", "requestBody": intent["requestBody"]}
	_, err := plugin.Engine.Call(t.Context(), "buildSubmitRequest", ctx)
	require.ErrorContains(t, err, "Referenced Kie task is unavailable")
	ctx["originTasks"] = []any{map[string]any{"taskId": "public-origin", "upstreamTaskId": "private-origin"}}
	sent := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
	input := sent["body"].(map[string]any)["input"].(map[string]any)
	assert.Equal(t, "private-origin", input["task_id"])
	assert.Equal(t, float64(0), input["index"])
	assert.Equal(t, "public-origin", intent["requestBody"].(map[string]any)["input"].(map[string]any)["task_id"], "driver must not mutate the decoded body")
	assert.Equal(t, float64(10), callKie(t, plugin, "extractUsage", nil, ctx)["seconds"])
	// Polling accepts either documented result representation. An empty parsed
	// response does not hide a populated resultJson on older vendor replies.
	for _, data := range []map[string]any{
		{"state": "success", "response": map[string]any{"resultUrls": []any{"https://cdn.example/movie.mp4"}}},
		{"state": "success", "response": map[string]any{}, "resultJson": `{"resultUrls":["https://cdn.example/movie.mp4"]}`},
	} {
		result := callKie(t, plugin, "parseTaskResult", nil, ctx, map[string]any{"code": 200, "data": data})
		assert.Equal(t, "SUCCESS", result["status"])
		assert.Equal(t, "https://cdn.example/movie.mp4", result["url"])
	}
	mediaCtx := map[string]any{"artifacts": map[string]any{"media_0": map[string]any{"key": "media_0", "type": "video", "url": "https://gateway.example/video?a=1&b=2"}}}
	events := callKie(t, plugin, "protocols", []string{"openai_responses", "renderEvents"}, mediaCtx, map[string]any{"status": "SUCCESS"})
	assert.True(t, events["done"].(bool))
	output := events["events"].([]any)
	require.Len(t, output, 1)
	assert.Equal(t, `<video controls src="https://gateway.example/video?a=1&amp;b=2"></video>`, output[0].(map[string]any)["data"])
	duplicate := callKie(t, plugin, "protocols", []string{"openai_responses", "renderEvents"}, mediaCtx, map[string]any{"status": "SUCCESS"}, map[string]any{"status": "SUCCESS"})
	assert.Empty(t, duplicate["events"])
	failure := callKie(t, plugin, "protocols", []string{"openai_responses", "renderEvents"}, map[string]any{}, map[string]any{"status": "FAILURE", "fail_reason": "upstream refused"})
	assert.True(t, failure["done"].(bool))
	require.Len(t, failure["events"], 1)
	assert.Equal(t, "upstream refused", failure["events"].([]any)[0].(map[string]any)["message"])
}

func TestKieGPTModelFamilies(t *testing.T) {
	plugin := newKiePlugin(t)
	models := []string{
		"gpt-image/1.5-text-to-image", "gpt-image/1.5-image-to-image",
		"gpt-image-2-text-to-image", "gpt-image-2-image-to-image",
		"gpt-image-2-5-flare-text-to-image", "gpt-image-2-5-flare-image-to-image",
		"gpt-image-2-5-sunburst-text-to-image", "gpt-image-2-5-sunburst-image-to-image",
		"gpt-image-2-6/flare-text-to-image", "gpt-image-2-6/flare-image-to-image",
		"gpt-image-2-6/sunburst-text-to-image", "gpt-image-2-6/sunburst-image-to-image",
		"gpt-image-2-6/economy-text-to-image", "gpt-image-2-6/economy-image-to-image",
	}
	for _, name := range models {
		t.Run(name, func(t *testing.T) {
			require.NotContains(t, plugin.Meta.Models, name)
			operation := "generate"
			req := map[string]any{"model": name, "prompt": "a blue teapot", "size": "1024x1024"}
			edit := strings.HasSuffix(name, "image-to-image")
			if edit {
				operation = "edit"
				req["image"] = "https://cdn.example/source.png"
			}
			intent := callKie(t, plugin, "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": name, "operation": operation, "body": map[string]any{"kind": "json", "value": req}})
			request := intent["requestBody"].(map[string]any)
			input := request["input"].(map[string]any)
			assert.Equal(t, "1:1", input["aspect_ratio"])
			if edit {
				assert.Equal(t, []any{"https://cdn.example/source.png"}, input["input_urls"])
			}
			assert.NotContains(t, input, "frame_count", "static images must not acquire GIF-only defaults")
			assert.NotContains(t, input, "frame_duration_ms")
			assert.NotContains(t, input, "size", "OpenAI size must not leak into the vendor GIF size field")
			ctx := map[string]any{"model": name, "upstreamModel": name, "baseUrl": "https://api.kie.example", "apiKey": "key", "requestBody": request}
			descriptor := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
			assert.Equal(t, request, descriptor["body"])
			native := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": descriptor["body"]}})
			canonical := native["model"].(string)
			require.Contains(t, plugin.Meta.Models, canonical)
			nativeRequest := native["requestBody"].(map[string]any)
			assert.Equal(t, operation, nativeRequest["operation"])
			assert.Equal(t, input, nativeRequest["input"])
			ctx["model"], ctx["upstreamModel"], ctx["requestBody"] = canonical, canonical, nativeRequest
			assert.Equal(t, descriptor["body"], callKie(t, plugin, "buildSubmitRequest", nil, ctx)["body"])
			facts := callKie(t, plugin, "extractUsage", nil, ctx)
			assert.Equal(t, float64(1), facts["image_count"])
			schema, _ := plugin.Meta.UsageForModel(canonical)
			require.Len(t, facts, len(schema))
			if !strings.HasPrefix(name, "gpt-image/1.5-") && !strings.Contains(name, "/economy-") {
				assert.Equal(t, "1K", facts["resolution"])
			}
		})
	}
	for _, tc := range []struct {
		name        string
		input, want map[string]any
	}{
		{"gpt-image-2-6/flare-text-to-image", map[string]any{"output_format": "webp", "output_compression": 0, "quality": "max", "resolution": "4K"}, map[string]any{"output_compression": float64(0), "quality": "max", "resolution": "4K"}},
		{"gpt-image-2-6/flare-text-to-image", map[string]any{"output_format": "gif", "size": "512x512", "frame_count": 16, "frame_duration_ms": 20}, map[string]any{"size": "512x512", "frame_count": float64(16), "frame_duration_ms": float64(20)}},
		{"gpt-image-2-6/sunburst-text-to-image", map[string]any{"output_format": "svg"}, map[string]any{"svg": map[string]any{"model": "gpt-5.6-luna"}}},
		{"gpt-image-2-6/economy-text-to-image", map[string]any{"output_format": "gif", "frame_count": "64"}, map[string]any{"frame_count": "64", "frame_duration_ms": "auto"}},
	} {
		t.Run(tc.name+" advanced input", func(t *testing.T) {
			tc.input["prompt"] = "a blue teapot"
			intent := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": map[string]any{"model": tc.name, "input": tc.input}}})
			input := intent["requestBody"].(map[string]any)["input"].(map[string]any)
			for key, want := range tc.want {
				assert.Equal(t, want, input[key], key)
			}
		})
	}
}

func TestKieUnifiedImageModels(t *testing.T) {
	plugin := newKiePlugin(t)
	assert.NotContains(t, plugin.Meta.Models, "google/nano-banana-edit")
	seen := map[string]bool{}
	for _, name := range plugin.Meta.Models {
		assert.False(t, seen[name], "duplicate channel model: %s", name)
		seen[name] = true
		if strings.HasPrefix(name, "gpt-image") {
			assert.False(t, strings.Contains(name, "text-to-image") || strings.Contains(name, "image-to-image"), name)
		}
	}
	for _, name := range []string{"nano-banana-pro", "nano-banana-2", "nano-banana-2-1", "nano-banana-2-lite"} {
		for _, operation := range []string{"generate", "edit"} {
			req := map[string]any{"prompt": "a blue teapot"}
			if operation == "edit" {
				req["image"] = "https://cdn.example/source.png"
			}
			intent := callKie(t, plugin, "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": name, "operation": operation, "body": map[string]any{"kind": "json", "value": req}})
			wire := callKie(t, plugin, "buildSubmitRequest", nil, map[string]any{"model": name, "requestBody": intent["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"})
			assert.Equal(t, name, wire["body"].(map[string]any)["model"])
		}
	}
	for _, name := range []string{"google/imagen4", "google/imagen4-fast", "google/imagen4-ultra"} {
		_, err := plugin.Engine.CallPath(t.Context(), "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": name, "operation": "edit", "body": map[string]any{"kind": "json", "value": map[string]any{"prompt": "p", "image": "https://cdn.example/a.png"}}})
		require.ErrorContains(t, err, "does not accept image input")
	}
	families := []struct{ name, generate, edit string }{
		{"google/nano-banana", "google/nano-banana", "google/nano-banana-edit"},
		{"gpt-image-1.5", "gpt-image/1.5-text-to-image", "gpt-image/1.5-image-to-image"},
		{"gpt-image-2", "gpt-image-2-text-to-image", "gpt-image-2-image-to-image"},
		{"gpt-image-2.5-flare", "gpt-image-2-5-flare-text-to-image", "gpt-image-2-5-flare-image-to-image"},
		{"gpt-image-2.5-sunburst", "gpt-image-2-5-sunburst-text-to-image", "gpt-image-2-5-sunburst-image-to-image"},
		{"gpt-image-2.6-flare", "gpt-image-2-6/flare-text-to-image", "gpt-image-2-6/flare-image-to-image"},
		{"gpt-image-2.6-sunburst", "gpt-image-2-6/sunburst-text-to-image", "gpt-image-2-6/sunburst-image-to-image"},
		{"gpt-image-2.6-economy", "gpt-image-2-6/economy-text-to-image", "gpt-image-2-6/economy-image-to-image"},
	}
	for _, family := range families {
		for _, operation := range []string{"generate", "edit"} {
			t.Run(family.name+"/"+operation, func(t *testing.T) {
				require.Contains(t, plugin.Meta.Models, family.name)
				publicName := family.name
				req := map[string]any{"model": publicName, "prompt": "a blue teapot"}
				path := "/v1/images/generations"
				wantVendor := family.generate
				if operation == "edit" {
					path = "/v1/images/edits"
					req["image"] = "https://cdn.example/source.png"
					wantVendor = family.edit
				}
				protocolCtx := jsplugin.ProtocolRequestContext{
					RouteRequestContext: jsplugin.RouteRequestContext{Method: http.MethodPost, Path: path, Body: map[string]any{"kind": "json", "value": req}},
					Protocol:            jsplugin.ProtocolOpenAIImage, Operation: operation, Model: publicName,
				}
				c, _ := gin.CreateTestContext(httptest.NewRecorder())
				c.Request = httptest.NewRequest(http.MethodPost, path, nil)
				c.Set(jsplugin.ContextKeyPinnedEndpoint, jsplugin.PinnedEndpoint{Plugin: plugin, Protocol: jsplugin.ProtocolOpenAIImage, Model: publicName})
				c.Set(jsplugin.ContextKeyProtocolRequest, protocolCtx)
				info := &relaycommon.RelayInfo{
					OriginModelName: publicName,
					ChannelMeta:     &relaycommon.ChannelMeta{ChannelType: constant.ChannelTypeTaskPlugin, ChannelBaseUrl: "https://api.kie.example", ApiKey: "key", UpstreamModelName: publicName},
					TaskRelayInfo:   &relaycommon.TaskRelayInfo{PublicTaskID: "task_public"},
				}
				adaptor := taskplugin.New(plugin)
				adaptor.Init(info)
				require.Nil(t, adaptor.ValidateRequestAndSetAction(c, info))
				reader, err := adaptor.BuildRequestBody(c, info)
				require.NoError(t, err)
				var wire map[string]any
				require.NoError(t, common.DecodeJson(reader, &wire))
				assert.Equal(t, wantVendor, wire["model"])
				input := wire["input"].(map[string]any)
				imageField := "input_urls"
				if family.name == "google/nano-banana" {
					imageField = "image_urls"
				}
				if operation == "edit" {
					assert.Equal(t, []any{"https://cdn.example/source.png"}, input[imageField])
				} else {
					assert.NotContains(t, input, imageField)
				}
				responsesBody := map[string]any{"input": "a blue teapot"}
				if operation == "edit" {
					responsesBody[imageField] = []any{"https://cdn.example/source.png"}
				}
				responses := callKie(t, plugin, "protocols", []string{"openai_responses", "decodeRequest"}, map[string]any{"model": publicName, "body": map[string]any{"kind": "json", "value": responsesBody}})
				assert.Equal(t, operation, responses["requestBody"].(map[string]any)["operation"])
				native := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": wire}})
				assert.Equal(t, publicName, native["model"])
				assert.Equal(t, operation, native["requestBody"].(map[string]any)["operation"])
				// Body routing must not replace the caller's billing/display identity.
				assert.Equal(t, publicName, info.OriginModelName)
				assert.Equal(t, publicName, info.UpstreamModelName)
				facts, err := adaptor.ExtractUsageFactsValidated(c, info)
				require.NoError(t, err)
				assert.Equal(t, float64(1), facts["image_count"])
				schema, _ := plugin.Meta.UsageForModel(publicName)
				require.Len(t, facts, len(schema))
				// Polling has no requestBody; the unified image model still settles its
				// actual image quantity with the same schema as both vendor operations.
				body := []byte(`{"code":200,"data":{"state":"success","resultJson":"{\"resultUrls\":[\"https://cdn.example/result.png\"]}"}}`)
				task := &model.Task{TaskID: "task_public", Action: "image", Properties: model.Properties{OriginModelName: publicName, UpstreamModelName: publicName}}
				completed, err := adaptor.ParseTaskResult(task, &http.Response{StatusCode: http.StatusOK}, body)
				require.NoError(t, err)
				assert.Equal(t, "SUCCESS", completed.Status)
				assert.Equal(t, float64(1), completed.UsageFacts["image_count"])
			})
		}
	}
}

func TestKieUnifiedImagesThroughGatewayAndAlias(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, operation := range []string{"generate", "edit"} {
		t.Run(operation, func(t *testing.T) {
			req := map[string]any{"model": "custom-image-alias", "prompt": "a blue teapot"}
			if operation == "edit" {
				req["image"] = "https://cdn.example/input.png"
			}
			intent := callKie(t, plugin, "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": "custom-image-alias", "upstreamModel": "gpt-image-2.6-flare", "operation": operation, "body": map[string]any{"kind": "json", "value": req}})
			assert.Equal(t, "custom-image-alias", intent["model"])
			normalized := intent["requestBody"].(map[string]any)
			assert.Equal(t, operation, normalized["operation"])
			downstream := map[string]any{"model": "custom-image-alias", "upstreamModel": "gpt-image-2.6-flare", "requestBody": normalized, "baseUrl": "https://gateway.example", "apiKey": "gateway-key", "upstream": map[string]any{"kind": "new_api"}}
			forwarded := callKie(t, plugin, "buildSubmitRequest", nil, downstream)
			assert.Equal(t, "https://gateway.example/kie/api/v1/jobs/createTask", forwarded["url"])
			assert.Equal(t, "gpt-image-2.6-flare", forwarded["body"].(map[string]any)["model"])
			native := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"body": map[string]any{"kind": "json", "value": forwarded["body"]}})
			assert.Equal(t, operation, native["requestBody"].(map[string]any)["operation"])
			upstream := map[string]any{"model": "gpt-image-2.6-flare", "upstreamModel": "gpt-image-2.6-flare", "requestBody": native["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "vendor-key"}
			sent := callKie(t, plugin, "buildSubmitRequest", nil, upstream)
			wantModel := "gpt-image-2-6/flare-text-to-image"
			if operation == "edit" {
				wantModel = "gpt-image-2-6/flare-image-to-image"
			}
			assert.Equal(t, wantModel, sent["body"].(map[string]any)["model"])
			assert.Equal(t, forwarded["body"].(map[string]any)["input"], sent["body"].(map[string]any)["input"])
			assert.Equal(t, callKie(t, plugin, "extractUsage", nil, downstream), callKie(t, plugin, "extractUsage", nil, upstream))
		})
	}
	for _, tc := range []struct {
		operation string
		body      map[string]any
		want      string
	}{
		{"edit", map[string]any{"prompt": "p"}, "input image URL is required"},
		{"generate", map[string]any{"prompt": "p", "image": "https://cdn.example/a.png"}, "does not accept image input"},
		{"generate", map[string]any{"prompt": "p", "operation": "edit", "metadata": map[string]any{"input_urls": []any{"https://cdn.example/a.png"}}}, "Unsupported Kie input field"},
		{"edit", map[string]any{"prompt": "p", "image": "https://cdn.example/a.png", "metadata": map[string]any{"max_images": 129}}, "Unsupported Kie input field"},
	} {
		_, err := plugin.Engine.CallPath(t.Context(), "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": "gpt-image-2", "operation": tc.operation, "body": map[string]any{"kind": "json", "value": tc.body}})
		require.ErrorContains(t, err, tc.want)
	}
	for _, withImage := range []bool{false, true} {
		input := []any{map[string]any{"role": "user", "content": []any{map[string]any{"type": "input_text", "text": "a blue teapot"}}}}
		if withImage {
			input[0].(map[string]any)["content"] = append(input[0].(map[string]any)["content"].([]any), map[string]any{"type": "input_image", "image_url": "https://cdn.example/a.png"})
		}
		decoded := callKie(t, plugin, "protocols", []string{"openai_responses", "decodeRequest"}, map[string]any{"model": "gpt-image-2", "body": map[string]any{"kind": "json", "value": map[string]any{"input": input}}})
		want := "generate"
		if withImage {
			want = "edit"
		}
		assert.Equal(t, want, decoded["requestBody"].(map[string]any)["operation"])
	}
}

func TestKieOfficialGoogleImageModelNames(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, tc := range []struct{ official, generate, edit string }{
		{"gemini-2.5-flash-image", "google/nano-banana", "google/nano-banana-edit"},
		{"gemini-3-pro-image", "nano-banana-pro", "nano-banana-pro"},
		{"gemini-3.1-flash-image", "nano-banana-2", "nano-banana-2"},
		{"gemini-nano-banana-2.1", "nano-banana-2-1", "nano-banana-2-1"},
		{"gemini-3.1-flash-lite-image", "nano-banana-2-lite", "nano-banana-2-lite"},
	} {
		t.Run(tc.official, func(t *testing.T) {
			assert.Contains(t, plugin.Meta.Models, tc.official)
			for _, operation := range []string{"generate", "edit"} {
				body := map[string]any{"prompt": "a blue teapot"}
				if operation == "edit" {
					body["image"] = "https://cdn.example/source.png"
				}
				intent := callKie(t, plugin, "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": tc.official, "operation": operation, "body": map[string]any{"kind": "json", "value": body}})
				assert.Equal(t, tc.official, intent["model"])
				ctx := map[string]any{"model": tc.official, "requestBody": intent["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"}
				wire := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				want := tc.generate
				if operation == "edit" {
					want = tc.edit
				}
				assert.Equal(t, want, wire["body"].(map[string]any)["model"])
				facts := callKie(t, plugin, "extractUsage", nil, ctx)
				assert.Equal(t, float64(1), facts["image_count"])
				ctx["upstream"] = map[string]any{"kind": "new_api"}
				forwarded := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				assert.Equal(t, tc.official, forwarded["body"].(map[string]any)["model"])
				if operation == "edit" {
					_, err := plugin.Engine.CallPath(t.Context(), "protocols", []string{"openai_image", "decodeRequest"}, map[string]any{"model": tc.official, "operation": operation, "body": map[string]any{"kind": "json", "value": map[string]any{"prompt": "p"}}})
					require.Error(t, err)
				}
			}
		})
	}
}

func TestKieOfficialAliasesPreserveVendorRequestsAndUsage(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, tc := range []struct {
		official, generate, edit, protocol string
		body                               map[string]any
	}{
		{"flux-2-pro", "flux-2/pro-text-to-image", "flux-2/pro-image-to-image", "openai_image", map[string]any{"prompt": "p", "aspect_ratio": "1:1", "resolution": "1K"}},
		{"flux-2-flex", "flux-2/flex-text-to-image", "flux-2/flex-image-to-image", "openai_image", map[string]any{"prompt": "p", "aspect_ratio": "1:1", "resolution": "1K"}},
		{"imagen-4.0-generate-001", "google/imagen4", "", "openai_image", map[string]any{"prompt": "p", "aspect_ratio": "1:1"}},
		{"imagen-4.0-fast-generate-001", "google/imagen4-fast", "", "openai_image", map[string]any{"prompt": "p", "aspect_ratio": "1:1"}},
		{"imagen-4.0-ultra-generate-001", "google/imagen4-ultra", "", "openai_image", map[string]any{"prompt": "p", "aspect_ratio": "1:1"}},
		{"wan2.6-t2v", "wan/2-6-text-to-video", "", "openai_video", map[string]any{"prompt": "p", "seconds": 5}},
		{"wan2.6-i2v", "wan/2-6-image-to-video", "", "openai_video", map[string]any{"prompt": "p", "seconds": 5, "image": "https://cdn.example/source.png"}},
		{"wan2.5-t2v-preview", "wan/2-5-text-to-video", "", "openai_video", map[string]any{"prompt": "p", "seconds": 5, "resolution": "720p"}},
		{"wan2.5-i2v-preview", "wan/2-5-image-to-video", "", "openai_video", map[string]any{"prompt": "p", "seconds": 5, "resolution": "720p", "image": "https://cdn.example/source.png"}},
	} {
		t.Run(tc.official, func(t *testing.T) {
			assert.Contains(t, plugin.Meta.Models, tc.official)
			assert.Contains(t, plugin.Meta.Models, tc.generate, "existing channel aliases must remain available")
			operations := []string{"generate"}
			if tc.edit != "" {
				operations = append(operations, "edit")
			}
			for _, operation := range operations {
				body := map[string]any{}
				for k, v := range tc.body {
					body[k] = v
				}
				vendor := tc.generate
				if operation == "edit" {
					body["image"] = "https://cdn.example/source.png"
					vendor = tc.edit
				}
				intent := callKie(t, plugin, "protocols", []string{tc.protocol, "decodeRequest"}, map[string]any{"model": tc.official, "operation": operation, "body": map[string]any{"kind": "json", "value": body}})
				ctx := map[string]any{"model": tc.official, "requestBody": intent["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"}
				wire := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				assert.Equal(t, vendor, wire["body"].(map[string]any)["model"])
				facts := callKie(t, plugin, "extractUsage", nil, ctx)
				field, want := "image_count", float64(1)
				if tc.protocol == "openai_video" {
					field, want = "seconds", float64(5)
				}
				assert.Equal(t, want, facts[field])
				schema, _ := plugin.Meta.UsageForModel(tc.official)
				require.NotEmpty(t, schema)
				assert.Contains(t, schema, field)
				legacy := callKie(t, plugin, "protocols", []string{tc.protocol, "decodeRequest"}, map[string]any{"model": vendor, "operation": operation, "body": map[string]any{"kind": "json", "value": body}})
				legacyCtx := map[string]any{"model": vendor, "requestBody": legacy["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"}
				legacyWire := callKie(t, plugin, "buildSubmitRequest", nil, legacyCtx)
				assert.Equal(t, wire["body"], legacyWire["body"])
				assert.Equal(t, facts, callKie(t, plugin, "extractUsage", nil, legacyCtx))
				ctx["upstream"] = map[string]any{"kind": "new_api"}
				forwarded := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				assert.Equal(t, tc.official, forwarded["body"].(map[string]any)["model"])
			}
			if tc.protocol == "openai_image" && tc.edit == "" {
				_, err := plugin.Engine.CallPath(t.Context(), "protocols", []string{tc.protocol, "decodeRequest"}, map[string]any{"model": tc.official, "operation": "edit", "body": map[string]any{"kind": "json", "value": map[string]any{"prompt": "p", "image": "https://cdn.example/source.png"}}})
				require.Error(t, err, "Imagen aliases must remain text-only")
			}
		})
	}
}

func TestKieOfficialKlingModelsChooseVideoOperation(t *testing.T) {
	plugin := newKiePlugin(t)
	for _, tc := range []struct{ model, text, image string }{
		{"kling-v2-1-master", "kling/v2-1-master-text-to-video", "kling/v2-1-master-image-to-video"},
		{"kling-v2-6", "kling-2.6/text-to-video", "kling-2.6/image-to-video"},
		{"kling-v2-5-turbo", "kling/v2-5-turbo-text-to-video-pro", "kling/v2-5-turbo-image-to-video-pro"},
	} {
		for _, imageInput := range []bool{false, true} {
			t.Run(tc.model+map[bool]string{false: "/text", true: "/image"}[imageInput], func(t *testing.T) {
				body := map[string]any{"prompt": "p", "seconds": 5, "sound": true, "aspect_ratio": "16:9"}
				if tc.model != "kling-v2-6" {
					delete(body, "sound")
				}
				if imageInput {
					body["image"] = "https://cdn.example/source.png"
					delete(body, "aspect_ratio")
				}
				intent := callKie(t, plugin, "protocols", []string{"openai_video", "decodeRequest"}, map[string]any{"model": tc.model, "body": map[string]any{"kind": "json", "value": body}})
				ctx := map[string]any{"model": tc.model, "requestBody": intent["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"}
				wire := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				want := tc.text
				if imageInput {
					want = tc.image
				}
				assert.Equal(t, want, wire["body"].(map[string]any)["model"])
				facts := callKie(t, plugin, "extractUsage", nil, ctx)
				assert.Equal(t, float64(5), facts["seconds"])
				ctx["upstream"] = map[string]any{"kind": "new_api"}
				forwarded := callKie(t, plugin, "buildSubmitRequest", nil, ctx)
				assert.Equal(t, tc.model, forwarded["body"].(map[string]any)["model"])
				native := callKie(t, plugin, "native", []string{"createTask"}, map[string]any{"model": tc.model, "body": map[string]any{"kind": "json", "value": forwarded["body"]}})
				wire2 := callKie(t, plugin, "buildSubmitRequest", nil, map[string]any{"model": tc.model, "requestBody": native["requestBody"], "baseUrl": "https://api.kie.example", "apiKey": "key"})
				assert.Equal(t, wire["body"], wire2["body"])
			})
		}
	}
}
