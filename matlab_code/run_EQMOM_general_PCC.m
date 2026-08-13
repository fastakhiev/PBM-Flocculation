%% GENERAL PCC EQMOM RUNNER
% Required files in the same MATLAB folder:
%   fit_EQMOM_general_PCC.m
%   computeLogNormalNew.m
%   computeGaussWigert.m
%
% For each PCC, replace TIME, DF_exp, d43_exp, M0, and DF_max.

clear;
clc;
close all;

%% =======================================================================
% 1. ENTER DATA FOR ONE PCC CASE
% ========================================================================

TIME = [0;0.5;1.4;2.3;3.3;4.2;5.1;6.0;6.9;7.9;8.8;9.7; ...
        10.6;11.5;12.5;13.4;14.3];


d43_exp = [0.414	;11.525;	23.135;	26.589;	32.217;	35.977;	38.49;	40.546;	41.7;	42.719;	43.467;	44.048;	44.808;	45.788;	46.564;	46.978;	47.484]

DF_exp = [1.65;1.65;	1.7925;	1.8982	;1.9764	;2.0343	;2.0773	;2.1091	;2.1326;	2.1501;	2.163;	2.1726;	2.1797;	2.185;	2.1889;	2.1918;	2.1939]

M0 = [1;0.57;0.82;1.8;7]

DF_max = 2.19;
%% =======================================================================
% 2. OPTIONAL SETTINGS
% ========================================================================

options = struct;
options.caseName = 'PCC example';

% Initial guess and bounds: [alpha_max,B]
options.p0 = [0.70,40.2];
options.lb = [1e-6,1e-8];
options.ub = [1.00,360.0];

% Multi-start points improve the chance of finding a lower SSE.
options.startPoints = [ ...
    0.10, 20; ...
    0.15, 30; ...
    0.20, 40; ...
    0.25,50; ...
    0.30,50; ...
    0.35,55; ...
    0.35,60; ...
    0.40,65; ...
    0.45,70; ...
    0.50,75; ...
    0.55,80; ...
    0.60,85; ...
    0.65,90; ...
    0.70,95; ...
    0.75,100; ...
    0.80,110; ...
    0.85,120; ...
    0.90,130; ...
    0.95,140; ...
    0.99,400];

% Model constants.
options.dt = 1.0;
options.G = 312;
options.v = 1e-6;
options.T = 296;
options.kB = 1.380622e-23;
options.mu = 1e-3;
options.d0 = 0.1;
options.x = 0.1;
options.y = 0.20;
options.n = 2;
options.Q = 5;

% PCC source normally uses exponent DF*y.
% Use 2.0 only for a model variant using DF*2*y.
options.sizePenaltyMultiplier = 1.0;

% Use 1.0 when M4/M3 is already in d43 units.
% Use 0.1 when physical d43 = 0.1*(M4/M3).
options.d43Scale = 1.0;

% Estimate gamma from DF_exp.
options.fitGamma = true;
options.gammaLower = 0.0;
options.gammaUpper = 10.0;

% The initial DF and d43 values are fixed by DF0 and M0.
options.excludeInitialPoint = true;

% Continue optimization after first reaching this GOF.
options.gofTarget = 0.93;
options.invalidPenaltyFactor = 4.0;

% Optimizer controls.
options.stage1Display = 'iter';
options.stage1MaxIterations = 300;
options.stage1MaxEvaluations = 1000;

options.display = 'iter';
options.maxIterations = 500;
options.maxEvaluations = 3000;
options.functionTolerance = 1e-9;
options.stepTolerance = 1e-9;
options.optimalityTolerance = 1e-8;

% Figures and results file.
options.makePlots = true;
options.saveResults = true;
options.resultFile = 'PCC_example_general_results.mat';

%% =======================================================================
% 3. RUN OPTIMIZATION
% ========================================================================

results = fit_EQMOM_general_PCC( ...
    TIME,DF_exp,d43_exp,M0,DF_max,options);

%% =======================================================================
% 4. PRINT OPTIMIZED VALUES
% ========================================================================

fprintf('\n============================================================\n');
fprintf('RETURNED GENERAL PCC RESULTS\n');
fprintf('============================================================\n');
fprintf('gamma                  = %.12g min^-1\n',results.gamma);
fprintf('alpha_max              = %.12g\n',results.alpha_max);
fprintf('B                      = %.12g\n',results.B);
fprintf('Valid optimization     = %d\n',results.optimizationSuccess);
fprintf('DF SSE                 = %.12g\n',results.DF_SSE);
fprintf('DF RMSE                = %.12g\n',results.DF_RMSE);
fprintf('DF R2                  = %.12g\n',results.DF_R2);
fprintf('d43 SSE                = %.12g\n',results.d43_SSE);
fprintf('d43 RMSE               = %.12g\n',results.d43_RMSE);
fprintf('d43 R2                 = %.12g\n',results.d43_R2);
fprintf('d43 GOF                = %.6f%%\n',results.GOF_percent);
fprintf('GOF target achieved    = %d\n',results.gofTargetAchieved);
fprintf('Initial point excluded = %d\n',results.excludeInitialPoint);
fprintf('============================================================\n');
