import torch
import torch.nn.functional as functional
from torch import nn


def gradient_magnitude(image):
    sobel_x = image.new_tensor(
        [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]
    ).view(1, 1, 3, 3)
    sobel_y = sobel_x.transpose(2, 3)
    grad_x = functional.conv2d(image, sobel_x, padding=1)
    grad_y = functional.conv2d(image, sobel_y, padding=1)
    return torch.sqrt(grad_x.square() + grad_y.square() + 1e-12)


def normalize_gradient(gradient):
    scale = gradient.mean((2, 3), keepdim=True).clamp_min(1e-6)
    return (gradient / scale).clamp(0.0, 5.0)


def build_reliability_target(
    rgb,
    high_resolution_depth,
    minimum_reliability=0.2,
    edge_center=1.0,
    sharpness=2.0,
):
    luminance = (
        0.299 * rgb[:, 0:1]
        + 0.587 * rgb[:, 1:2]
        + 0.114 * rgb[:, 2:3]
    )
    rgb_gradient = normalize_gradient(gradient_magnitude(luminance))
    depth_gradient = normalize_gradient(gradient_magnitude(high_resolution_depth))
    rgb_edge = torch.sigmoid(sharpness * (rgb_gradient - edge_center))
    depth_support = torch.sigmoid(sharpness * (depth_gradient - edge_center))
    unreliable = rgb_edge * (1.0 - depth_support)
    return 1.0 - (1.0 - minimum_reliability) * unreliable


class SpatialReliabilityGate(nn.Module):
    def __init__(self, hidden_channels=8, initial_bias=4.0):
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv2d(3, hidden_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, hidden_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, 1, 3, padding=1),
        )
        nn.init.normal_(self.network[-1].weight, mean=0.0, std=1e-3)
        nn.init.constant_(self.network[-1].bias, initial_bias)

    def forward(self, rgb, low_resolution_depth):
        luminance = (
            0.299 * rgb[:, 0:1]
            + 0.587 * rgb[:, 1:2]
            + 0.114 * rgb[:, 2:3]
        )
        depth_up = functional.interpolate(
            low_resolution_depth,
            size=rgb.shape[-2:],
            mode="bicubic",
            align_corners=False,
        )
        rgb_gradient = normalize_gradient(gradient_magnitude(luminance))
        depth_gradient = normalize_gradient(gradient_magnitude(depth_up))
        disagreement = torch.abs(rgb_gradient - depth_gradient)
        logits = self.network(
            torch.cat((rgb_gradient, depth_gradient, disagreement), dim=1)
        )
        return torch.sigmoid(logits)


class SGNetWithReliabilityGate(nn.Module):
    def __init__(self, base_model, hidden_channels=8, initial_bias=4.0):
        super().__init__()
        self.base_model = base_model
        self.reliability_gate = SpatialReliabilityGate(
            hidden_channels=hidden_channels,
            initial_bias=initial_bias,
        )

    def _select_gate(self, gate, mode):
        if mode == "learned":
            return gate
        if mode == "identity":
            return torch.ones_like(gate)
        if mode == "shuffled":
            return torch.roll(
                gate,
                shifts=(gate.shape[-2] // 2, gate.shape[-1] // 2),
                dims=(-2, -1),
            )
        if mode == "constant_mean":
            return gate.mean((2, 3), keepdim=True).expand_as(gate)
        raise ValueError(f"Unsupported gate mode: {mode}")

    def _apply_gate(
        self,
        features,
        gate,
        application,
        adaptive_threshold=0.75,
        adaptive_temperature=0.01,
    ):
        if application == "full":
            return features * gate
        if application in (
            "high_frequency",
            "adaptive",
            "soft_adaptive",
            "ramp_adaptive",
        ):
            low_frequency = functional.avg_pool2d(
                features,
                kernel_size=3,
                stride=1,
                padding=1,
            )
            high_frequency_gated = low_frequency + gate * (features - low_frequency)
            if application == "high_frequency":
                return high_frequency_gated
            full_gated = features * gate
            if application == "soft_adaptive":
                if adaptive_temperature <= 0:
                    raise ValueError("adaptive_temperature must be positive")
                high_frequency_weight = torch.sigmoid(
                    (adaptive_threshold - gate.mean((1, 2, 3), keepdim=True))
                    / adaptive_temperature
                )
                return full_gated + high_frequency_weight * (
                    high_frequency_gated - full_gated
                )
            if application == "ramp_adaptive":
                if adaptive_temperature <= 0:
                    raise ValueError("adaptive_temperature must be positive")
                high_frequency_weight = (
                    (adaptive_threshold - gate.mean((1, 2, 3), keepdim=True))
                    / adaptive_temperature
                ).clamp(0.0, 1.0)
                return full_gated + high_frequency_weight * (
                    high_frequency_gated - full_gated
                )
            use_high_frequency = gate.mean((1, 2, 3), keepdim=True) < adaptive_threshold
            return torch.where(use_high_frequency, high_frequency_gated, full_gated)
        raise ValueError(f"Unsupported gate application: {application}")

    def forward(
        self,
        inputs,
        gate_mode="learned",
        gate_application="full",
        adaptive_threshold=0.75,
        adaptive_temperature=0.01,
        return_gate=False,
    ):
        image, depth = inputs
        base = self.base_model

        out_re, grad_d4 = base.gradNet(depth, image)

        dp_in = base.act(base.conv_dp1(depth))
        dp1 = base.dp_rg1(dp_in)
        dp1_ = base.c_grad(torch.cat([dp1, grad_d4], dim=1))

        rgb1 = base.act(base.conv_rgb1(image))
        rgb2 = base.rgb_rb2(rgb1)
        gate = self._select_gate(
            self.reliability_gate(image, depth),
            gate_mode,
        )
        gated_rgb2 = self._apply_gate(
            rgb2,
            gate,
            gate_application,
            adaptive_threshold=adaptive_threshold,
            adaptive_temperature=adaptive_temperature,
        )
        ca1_in, r1 = base.bridge1(dp1_, gated_rgb2)

        dp2 = base.dp_rg2(torch.cat([dp1, ca1_in + dp_in], 1))
        dp2_ = base.c_grad2(torch.cat([dp2, grad_d4], dim=1))

        rgb3 = base.rgb_rb3(r1)
        ca2_in, r2 = base.bridge2(dp2_, rgb3)
        ca2_in_ = ca2_in + base.conv_dp2(dp_in)
        dp3 = base.dp_rg3(base.c_de(torch.cat([dp2, ca2_in_], 1)))

        rgb4 = base.rgb_rb4(r2)
        dp3_ = base.c_grad3(torch.cat([dp3, grad_d4], dim=1))
        ca3_in, _ = base.bridge3(dp3_, rgb4)

        dp4 = base.dp_rg4(base.c_rd(torch.cat([dp1, dp2, dp3, ca3_in], 1)))
        tail_in = base.upsampler(dp4)
        out = base.last_conv(base.tail(tail_in))
        out = out + base.bicubic(depth)

        if return_gate:
            return out, out_re, gate
        return out, out_re
