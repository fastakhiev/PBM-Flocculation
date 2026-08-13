function results = fit_EQMOM_general_PCC( ...
    TIME,DF_exp,d43_exp,M0,DF_max,options)
%FIT_EQMOM_GENERAL_PCC
% General two-stage EQMOM optimizer for different PCC datasets.
%
% REQUIRED INPUTS
%   TIME      : measurement times in minutes, including TIME(1)=0
%   DF_exp    : experimental fractal-dimension values
%   d43_exp   : experimental d43 values
%   M0        : initial moments [M0;M1;M2;M3;M4]
%   DF_max    : limiting fractal dimension
%
% OPTIONAL INPUT
%   options   : settings structure
%
% Stage 1 estimates gamma from DF_exp.
% Stage 2 fixes gamma and estimates [alpha_max,B] from d43_exp.
%
% By default, measurement 1 is excluded from both fit statistics because
% DF(0) is fixed by DF_exp(1) and d43(0) is fixed by M0. The initial point
% is still included in the returned trajectories and figures.
%
% Invalid/NaN Stage-2 trajectories receive a finite medium penalty so the
% optimizer continues. Only complete valid trajectories can be archived
% and reported as optimized solutions. Optimization continues after the
% requested GOF target is reached and retains the lowest-SSE valid result.
%
% Required functions on the MATLAB path:
%   computeLogNormalNew.m
%   computeGaussWigert.m

if nargin < 5
    error(['Required inputs: TIME, DF_exp, d43_exp, M0, ', ...
           'and DF_max.']);
end

if nargin < 6 || isempty(options)
    options = struct;
end

%% =======================================================================
% INPUT VALIDATION
% ========================================================================

TIME = TIME(:);
DF_exp = DF_exp(:);
d43_exp = d43_exp(:);
M0 = M0(:);

if numel(TIME) ~= numel(DF_exp)
    error('TIME and DF_exp must have the same number of values.');
end

if numel(TIME) ~= numel(d43_exp)
    error('TIME and d43_exp must have the same number of values.');
end

if numel(TIME) < 4
    error('At least four measurements are required.');
end

if TIME(1) ~= 0 || any(diff(TIME) <= 0)
    error('TIME must begin at zero and be strictly increasing.');
end

if any(~isfinite(TIME)) || any(~isfinite(DF_exp)) || ...
        any(~isfinite(d43_exp)) || ~isreal(TIME) || ...
        ~isreal(DF_exp) || ~isreal(d43_exp)
    error('TIME, DF_exp, and d43_exp must be finite and real.');
end

if numel(M0) ~= 5 || any(~isfinite(M0)) || ...
        ~isreal(M0) || any(M0 <= 0)
    error('M0 must be five positive finite real moments.');
end

if ~isscalar(DF_max) || ~isfinite(DF_max) || ~isreal(DF_max)
    error('DF_max must be one finite real scalar.');
end

if exist('computeLogNormalNew','file') == 0
    error('computeLogNormalNew.m was not found on the MATLAB path.');
end

if exist('computeGaussWigert','file') == 0
    error('computeGaussWigert.m was not found on the MATLAB path.');
end

%% =======================================================================
% SETTINGS
% ========================================================================

cfg = struct;

cfg.TIME = TIME;
cfg.dt = getOption(options,'dt',1.0);
cfg.sampleStep = round(TIME*60/cfg.dt);
cfg.nSteps = cfg.sampleStep(end);

if cfg.sampleStep(1) ~= 0 || any(diff(cfg.sampleStep) <= 0)
    error('Reduce options.dt so all TIME values map to unique time steps.');
end

cfg.M0 = M0;
cfg.DF0 = getOption(options,'DF0',DF_exp(1));
cfg.DF_max = DF_max;
cfg.gamma = NaN;

if ~isscalar(cfg.DF0) || ~isfinite(cfg.DF0) || ...
        ~isreal(cfg.DF0) || cfg.DF0 <= 0
    error('options.DF0 must be one positive finite real scalar.');
end

cfg.v = getOption(options,'v',1e-6);
cfg.G = getOption(options,'G',312);
cfg.epsilon = cfg.G^2*cfg.v;
cfg.T = getOption(options,'T',296);
cfg.kB = getOption(options,'kB',1.380622e-23);
cfg.mu = getOption(options,'mu',1e-3);
cfg.d0 = getOption(options,'d0',0.1);
cfg.D0 = getOption(options,'D0',cfg.d0*1e-6);
cfg.x = getOption(options,'x',0.1);
cfg.y = getOption(options,'y',0.2);
cfg.n = getOption(options,'n',2);
cfg.Q = getOption(options,'Q',5);

% Preserve the supplied PCC expression:
%   sizePenalty exponent = DF*y
cfg.sizePenaltyMultiplier = ...
    getOption(options,'sizePenaltyMultiplier',1.0);

% Use 1.0 when M4/M3 is already in the same units as d43_exp.
cfg.d43Scale = getOption(options,'d43Scale',1.0);

% Adaptive moment integration.
cfg.minSubstep = getOption(options,'minSubstep',cfg.dt/1024);
cfg.maximumSubsteps = getOption(options,'maximumSubsteps',4096);
cfg.sigmaMinimum = getOption(options,'sigmaMinimum',1e-12);

% Optimization and GOF.
p0 = getOption(options,'p0',[0.365,56.5]);
lb = getOption(options,'lb',[1e-6,1e-8]);
ub = getOption(options,'ub',[1.00,500.0]);

p0 = p0(:)';
lb = lb(:)';
ub = ub(:)';

if numel(p0) ~= 2 || numel(lb) ~= 2 || numel(ub) ~= 2
    error('p0, lb, and ub must each contain [alpha_max,B].');
end

if any(lb >= ub)
    error('Each lower bound must be smaller than its upper bound.');
end

p0 = min(max(p0,lb),ub);

excludeInitialPoint = ...
    getOption(options,'excludeInitialPoint',true);

if excludeInitialPoint
    fitIndices = (2:numel(TIME))';
else
    fitIndices = (1:numel(TIME))';
end

nFit = numel(fitIndices);

gofTarget = getOption(options,'gofTarget',0.90);
numberOfFittedParameters = ...
    getOption(options,'numberOfFittedParameters',3);

invalidPenaltyFactor = ...
    getOption(options,'invalidPenaltyFactor',4.0);

makePlots = getOption(options,'makePlots',true);
saveResults = getOption(options,'saveResults',true);
resultFile = getOption(options,'resultFile', ...
    'EQMOM_general_PCC_results.mat');
caseName = getOption(options,'caseName','PCC case');

startPoints = getOption(options,'startPoints',[ ...
    0.15,20; ...
    0.30,40; ...
    p0; ...
    0.50,80; ...
    0.70,120; ...
    0.90,200]);

startPoints = min(max(startPoints,lb),ub);

%% =======================================================================
% STAGE 1: ESTIMATE gamma FROM DF_exp
% ========================================================================

fitGamma = getOption(options,'fitGamma',true);
gammaLower = getOption(options,'gammaLower',0.0);
gammaUpper = getOption(options,'gammaUpper',10.0);

if fitGamma
    gammaObjective = @(gamma) DFObjective( ...
        gamma,cfg,DF_exp,fitIndices);

    gammaOptions = optimset( ...
        'Display',getOption(options,'stage1Display','iter'), ...
        'TolX',getOption(options,'stage1TolX',1e-10), ...
        'MaxIter',getOption(options,'stage1MaxIterations',300), ...
        'MaxFunEvals',getOption(options,'stage1MaxEvaluations',1000));

    [gammaHat,DF_SSE,stage1ExitFlag,stage1Output] = ...
        fminbnd(gammaObjective,gammaLower,gammaUpper,gammaOptions);
else
    gammaHat = getOption(options,'gamma',0.23);
    stage1ExitFlag = NaN;
    stage1Output = struct;
    stage1Output.message = 'Gamma supplied externally.';
end

cfg.gamma = gammaHat;
[DF_sample,DF_full] = simulateDF(cfg);

DF_residual_full = DF_sample-DF_exp;
DF_residual_fit = DF_residual_full(fitIndices);
DF_SSE = sum(DF_residual_fit.^2);
DF_RMSE = sqrt(mean(DF_residual_fit.^2));
DF_R2 = coefficientOfDetermination( ...
    DF_exp(fitIndices),DF_sample(fitIndices));

fprintf('\n============================================================\n');
fprintf('STAGE 1: DF FIT\n');
fprintf('Case                    = %s\n',caseName);
fprintf('Gamma fitted            = %d\n',fitGamma);
fprintf('gamma                   = %.12g min^-1\n',gammaHat);
fprintf('DF SSE                  = %.12g\n',DF_SSE);
fprintf('DF RMSE                 = %.12g\n',DF_RMSE);
fprintf('DF R2                   = %.12g\n',DF_R2);
fprintf('============================================================\n');

%% =======================================================================
% INITIAL DIAGNOSTICS
% ========================================================================

initialD43Model = ...
    cfg.d43Scale*cfg.M0(5)/cfg.M0(4);

fprintf('\n============================================================\n');
fprintf('GENERAL PCC INITIAL SETTINGS\n');
fprintf('Estimated gamma         = %.12g min^-1\n',cfg.gamma);
fprintf('DF0                     = %.12g\n',cfg.DF0);
fprintf('DF_max                  = %.12g\n',cfg.DF_max);
fprintf('Initial modeled d43     = %.12g\n',initialD43Model);
fprintf('Initial experimental d43= %.12g\n',d43_exp(1));
fprintf('Initial point excluded  = %d\n',excludeInitialPoint);
fprintf('GOF/SSE fit points      = %d\n',nFit);
fprintf('============================================================\n');

%% =======================================================================
% TRACKED MULTI-START OPTIMIZATION
% ========================================================================

emptyCandidate = struct( ...
    'found',false, ...
    'p',[NaN,NaN], ...
    'd43_model',NaN(size(d43_exp)), ...
    'DF_model',NaN(size(d43_exp)), ...
    'residual_fit',NaN(nFit,1), ...
    'SSE',Inf, ...
    'RMSE',NaN, ...
    'R2',NaN, ...
    'standardError',NaN, ...
    'GOF',-Inf, ...
    'evaluation',NaN, ...
    'simulationInfo',struct);

bestValid = emptyCandidate;
firstGOFTarget = emptyCandidate;
bestGOFTarget = emptyCandidate;

evaluationCount = 0;
nStarts = size(startPoints,1);
rawEndpoints = NaN(nStarts,2);
rawEndpointValid = false(nStarts,1);
exitFlags = NaN(nStarts,1);
optimizerOutputs = cell(nStarts,1);

residualFunction = @trackedResidual;

if exist('lsqnonlin','file') == 2
    solverOptions = optimoptions('lsqnonlin', ...
        'Display',getOption(options,'display','iter'), ...
        'FiniteDifferenceType','forward', ...
        'FunctionTolerance', ...
            getOption(options,'functionTolerance',1e-9), ...
        'StepTolerance', ...
            getOption(options,'stepTolerance',1e-9), ...
        'OptimalityTolerance', ...
            getOption(options,'optimalityTolerance',1e-8), ...
        'MaxIterations', ...
            getOption(options,'maxIterations',500), ...
        'MaxFunctionEvaluations', ...
            getOption(options,'maxEvaluations',3000));

    for s = 1:nStarts
        fprintf('\nPCC multi-start %d/%d: alpha=%.6g, B=%.6g\n', ...
            s,nStarts,startPoints(s,1),startPoints(s,2));

        [pRaw,~,~,exitFlags(s),optimizerOutputs{s}] = ...
            lsqnonlin(residualFunction,startPoints(s,:),lb,ub,solverOptions);

        rawEndpoints(s,:) = pRaw;

        [validRaw,~,~,~] = evaluateCandidate( ...
            pRaw,cfg,d43_exp,fitIndices,numberOfFittedParameters);

        rawEndpointValid(s) = validRaw;

        % Ensure the endpoint is archived if valid.
        trackedResidual(pRaw);
    end
else
    warning('lsqnonlin is unavailable; bounded multi-start fminsearch is used.');

    solverOptions = optimset( ...
        'Display',getOption(options,'display','iter'), ...
        'TolX',getOption(options,'stepTolerance',1e-8), ...
        'TolFun',getOption(options,'functionTolerance',1e-8), ...
        'MaxIter',getOption(options,'maxIterations',500), ...
        'MaxFunEvals',getOption(options,'maxEvaluations',3000));

    for s = 1:nStarts
        z0 = boundedToUnbounded(startPoints(s,:),lb,ub);

        objective = @(z) sum( ...
            residualFunction(unboundedToBounded(z,lb,ub)).^2);

        [zRaw,~,exitFlags(s),optimizerOutputs{s}] = ...
            fminsearch(objective,z0,solverOptions);

        pRaw = unboundedToBounded(zRaw,lb,ub);
        rawEndpoints(s,:) = pRaw;

        [validRaw,~,~,~] = evaluateCandidate( ...
            pRaw,cfg,d43_exp,fitIndices,numberOfFittedParameters);

        rawEndpointValid(s) = validRaw;
        trackedResidual(pRaw);
    end
end

%% =======================================================================
% SELECT ONLY A COMPLETE VALID SOLUTION
% ========================================================================

if bestValid.found
    selected = bestValid;
    optimizationSuccess = true;
else
    selected = emptyCandidate;
    optimizationSuccess = false;

    warning(['No complete valid PCC trajectory was found. ', ...
             'No alpha_max or B is reported.']);
end

if optimizationSuccess
    alphaMaxHat = selected.p(1);
    BHat = selected.p(2);
    d43_model = selected.d43_model;
    DF_model = selected.DF_model;
    d43_residual_fit = selected.residual_fit;
    d43_SSE = selected.SSE;
    d43_RMSE = selected.RMSE;
    d43_R2 = selected.R2;
    standardError = selected.standardError;
    GOF_user = selected.GOF;
    finalInfo = selected.simulationInfo;
else
    alphaMaxHat = NaN;
    BHat = NaN;
    d43_model = NaN(size(d43_exp));
    DF_model = DF_sample;
    d43_residual_fit = NaN(nFit,1);
    d43_SSE = NaN;
    d43_RMSE = NaN;
    d43_R2 = NaN;
    standardError = NaN;
    GOF_user = NaN;
    finalInfo = struct('valid',false);
end

gofTargetAchieved = optimizationSuccess && GOF_user >= gofTarget;

fprintf('\n============================================================\n');
fprintf('GENERAL PCC OPTIMIZATION RESULTS\n');
fprintf('Optimization valid      = %d\n',optimizationSuccess);
fprintf('Estimated gamma         = %.12g min^-1\n',cfg.gamma);

if optimizationSuccess
    fprintf('Optimized alpha_max     = %.12g\n',alphaMaxHat);
    fprintf('Optimized B             = %.12g\n',BHat);
    fprintf('d43 SSE                 = %.12g\n',d43_SSE);
    fprintf('d43 RMSE                = %.12g\n',d43_RMSE);
    fprintf('d43 R2                  = %.12g\n',d43_R2);
    fprintf('Standard error          = %.12g\n',standardError);
    fprintf('GOF                     = %.6f%%\n',100*GOF_user);
    fprintf('GOF target achieved     = %d\n',gofTargetAchieved);
end

fprintf('Total evaluations       = %d\n',evaluationCount);
fprintf('============================================================\n');

%% =======================================================================
% MODEL-VERSUS-EXPERIMENT FIGURES
% ========================================================================

if makePlots
    figure('Name',[caseName,' - DF model and experiment']);

    plot(TIME,DF_exp,'kx','LineWidth',1.5,'MarkerSize',8, ...
        'DisplayName','Experimental DF');
    hold on;
    plot(TIME,DF_sample,'--','LineWidth',1.8, ...
        'DisplayName','DF model');

    if excludeInitialPoint
        plot(TIME(1),DF_exp(1),'ko','MarkerSize',10, ...
            'DisplayName','Initial point excluded');
    end

    xlabel('Time (min)');
    ylabel('DF');
    title(sprintf('%s: DF model and experiment, \\gamma=%.5g min^{-1}', ...
        caseName,cfg.gamma));
    legend('Location','best');
    grid on;
    box on;

    figure('Name',[caseName,' - d43 model and experiment']);

    plot(TIME,d43_exp,'kx','LineWidth',1.5,'MarkerSize',8, ...
        'DisplayName','Experimental d_{43}');
    hold on;

    if optimizationSuccess
        plot(TIME,d43_model,'--','LineWidth',1.8, ...
            'DisplayName','Optimized EQMOM model');
    end

    if excludeInitialPoint
        plot(TIME(1),d43_exp(1),'ko','MarkerSize',10, ...
            'DisplayName','Initial point excluded');
    end

    xlabel('Time (min)');
    ylabel('d_{43}');
    legend('Location','best');
    grid on;
    box on;

    if optimizationSuccess
        title(sprintf(['%s: \\alpha_{max}=%.5g, B=%.5g, ', ...
            'GOF=%.2f%%'],caseName,alphaMaxHat,BHat,100*GOF_user));
    else
        title([caseName,': no complete valid Stage-2 solution']);
    end
end

%% =======================================================================
% RESULTS
% ========================================================================

results = struct;

results.caseName = caseName;
results.inputs.TIME = TIME;
results.inputs.DF_exp = DF_exp;
results.inputs.d43_exp = d43_exp;
results.inputs.M0 = M0;
results.inputs.DF_max = DF_max;
results.options = options;
results.cfg = cfg;

results.gamma = gammaHat;
results.alpha_max = alphaMaxHat;
results.B = BHat;
results.optimizationSuccess = optimizationSuccess;

results.fitIndices = fitIndices;
results.excludeInitialPoint = excludeInitialPoint;
results.numberOfFitPoints = nFit;
results.numberOfFittedParameters = numberOfFittedParameters;

results.initialD43Model = initialD43Model;
results.DF_exp = DF_exp;
results.DF_model = DF_sample;
results.DF_full = DF_full;
results.DF_residual_full = DF_residual_full;
results.DF_residual_fit = DF_residual_fit;
results.DF_SSE = DF_SSE;
results.DF_RMSE = DF_RMSE;
results.DF_R2 = DF_R2;
results.stage1ExitFlag = stage1ExitFlag;
results.stage1Output = stage1Output;
results.d43_model = d43_model;
results.DF_model_stage2 = DF_model;
results.d43_residual_fit = d43_residual_fit;

results.d43_SSE = d43_SSE;
results.d43_RMSE = d43_RMSE;
results.d43_R2 = d43_R2;
results.standardError = standardError;
results.GOF_user = GOF_user;
results.GOF_percent = 100*GOF_user;

results.gofTarget = gofTarget;
results.gofTargetAchieved = gofTargetAchieved;
results.firstGOFTarget = firstGOFTarget;
results.bestGOFTarget = bestGOFTarget;
results.bestValid = bestValid;

results.finalSimulationInfo = finalInfo;
results.evaluationCount = evaluationCount;
results.startPoints = startPoints;
results.rawEndpoints = rawEndpoints;
results.rawEndpointValid = rawEndpointValid;
results.exitFlags = exitFlags;
results.optimizerOutputs = optimizerOutputs;

if saveResults
    try
        save(resultFile,'results');
        fprintf('\nResults saved to:\n%s\n',fullfile(pwd,resultFile));
    catch saveError
        fallbackFile = fullfile(tempdir,resultFile);

        warning(['Could not save in the current folder: %s\n', ...
                 'Saving in tempdir instead.'],saveError.message);

        save(fallbackFile,'results');
        fprintf('\nResults saved to:\n%s\n',fallbackFile);
    end
end

%% =======================================================================
% NESTED TRACKING RESIDUAL
% ========================================================================

    function residual = trackedResidual(p)
        evaluationCount = evaluationCount+1;

        [valid,d43Candidate,DFCandidate,candidate] = ...
            evaluateCandidate( ...
                p,cfg,d43_exp,fitIndices,numberOfFittedParameters);

        if valid
            candidate.evaluation = evaluationCount;

            if ~bestValid.found || candidate.SSE < bestValid.SSE
                bestValid = candidate;
            end

            if candidate.GOF >= gofTarget
                if ~firstGOFTarget.found
                    firstGOFTarget = candidate;

                    fprintf(['\n*** PCC GOF %.1f%% reached: ', ...
                        'evaluation=%d, alpha=%.10g, B=%.10g, ', ...
                        'SSE=%.10g, GOF=%.4f%% ***\n'], ...
                        100*gofTarget,evaluationCount, ...
                        candidate.p(1),candidate.p(2), ...
                        candidate.SSE,100*candidate.GOF);
                end

                if ~bestGOFTarget.found || ...
                        candidate.SSE < bestGOFTarget.SSE
                    bestGOFTarget = candidate;
                end
            end

            residual = candidate.residual_fit;
            return;
        end

        % Medium finite penalty for invalid/NaN/error candidates.
        dataScale = max(std(d43_exp(fitIndices)),1);
        normalizedP = (p(:)'-lb)./(ub-lb);
        direction = normalizedP(1)-normalizedP(2);

        residual = invalidPenaltyFactor*dataScale*ones(nFit,1) + ...
            0.05*dataScale*direction*linspace(-1,1,nFit)';

        bad = ~isfinite(residual) | ~isreal(residual);
        residual(bad) = invalidPenaltyFactor*dataScale;
    end

end


%% =======================================================================
function value = getOption(options,name,defaultValue)

if isstruct(options) && isfield(options,name) && ...
        ~isempty(options.(name))
    value = options.(name);
else
    value = defaultValue;
end
end


%% =======================================================================
function SSE = DFObjective(gamma,cfg,DF_exp,fitIndices)

cfgTrial = cfg;
cfgTrial.gamma = gamma;
DF_model = simulateDF(cfgTrial);
residual = DF_model(fitIndices)-DF_exp(fitIndices);
SSE = sum(residual.^2);
end


%% =======================================================================
function [DFsample,DFfull] = simulateDF(cfg)

DFfull = zeros(cfg.nSteps+1,1);
DFfull(1) = cfg.DF0;

for step = 1:cfg.nSteps
    DFfull(step+1) = DFfull(step) + ...
        (cfg.DF_max-DFfull(step))*cfg.gamma*cfg.dt/60;
end

DFsample = DFfull(cfg.sampleStep+1);
end


%% =======================================================================
function [valid,d43Model,DFModel,candidate] = ...
    evaluateCandidate(p,cfg,d43_exp,fitIndices,nParameters)

valid = false;
d43Model = NaN(size(d43_exp));
DFModel = NaN(size(d43_exp));

candidate = struct( ...
    'found',false, ...
    'p',p(:)', ...
    'd43_model',NaN(size(d43_exp)), ...
    'DF_model',NaN(size(d43_exp)), ...
    'residual_fit',NaN(numel(fitIndices),1), ...
    'SSE',Inf, ...
    'RMSE',NaN, ...
    'R2',NaN, ...
    'standardError',NaN, ...
    'GOF',-Inf, ...
    'evaluation',NaN, ...
    'simulationInfo',struct);

try
    [d43Trial,DFTrial,simulationInfo] = ...
        simulateEQMOMPCC(p(1),p(2),cfg);

    completeValid = simulationInfo.valid && ...
        numel(d43Trial)==numel(d43_exp) && ...
        all(isfinite(d43Trial)) && all(isreal(d43Trial));

    if ~completeValid
        return;
    end

    residualFit = ...
        d43Trial(fitIndices)-d43_exp(fitIndices);

    SSE = sum(residualFit.^2);
    RMSE = sqrt(mean(residualFit.^2));
    R2 = coefficientOfDetermination( ...
        d43_exp(fitIndices),d43Trial(fitIndices));

    degreesOfFreedom = numel(fitIndices)-nParameters;

    if degreesOfFreedom > 0
        standardError = sqrt(SSE/degreesOfFreedom);
    else
        standardError = NaN;
    end

    meanExperimental = mean(d43_exp(fitIndices));

    if isfinite(standardError) && abs(meanExperimental)>eps
        GOF = ...
            (meanExperimental-standardError)/meanExperimental;
    else
        GOF = NaN;
    end

    valid = isfinite(SSE) && isfinite(RMSE) && ...
        isfinite(GOF) && isreal(GOF);

    if ~valid
        return;
    end

    d43Model = d43Trial;
    DFModel = DFTrial;

    candidate.found = true;
    candidate.p = p(:)';
    candidate.d43_model = d43Trial;
    candidate.DF_model = DFTrial;
    candidate.residual_fit = residualFit;
    candidate.SSE = SSE;
    candidate.RMSE = RMSE;
    candidate.R2 = R2;
    candidate.standardError = standardError;
    candidate.GOF = GOF;
    candidate.simulationInfo = simulationInfo;

catch
    valid = false;
end
end


%% =======================================================================
function [d43Sample,DFsample,info] = ...
    simulateEQMOMPCC(alphaMax,B,cfg)

M = cfg.M0(:);

[DFsample,DFfull] = simulateDF(cfg);

d43Sample = NaN(numel(cfg.TIME),1);
d43Sample(1) = cfg.d43Scale*M(5)/M(4);

nextSample = 2;

info = struct;
info.valid = true;
info.failureTimeSeconds = NaN;
info.reason = '';
info.totalStepHalvings = 0;
info.acceptedSubsteps = 0;

for step = 1:cfg.nSteps
    DFnow = DFfull(step);

    [M,stepValid,stepInfo] = ...
        advanceAdaptive(M,DFnow,alphaMax,B,cfg);

    info.totalStepHalvings = ...
        info.totalStepHalvings+stepInfo.halvings;
    info.acceptedSubsteps = ...
        info.acceptedSubsteps+stepInfo.acceptedSubsteps;

    if ~stepValid
        info.valid = false;
        info.failureTimeSeconds = ...
            (step-1)*cfg.dt+stepInfo.advancedTime;
        info.reason = stepInfo.reason;
        return;
    end

    if nextSample <= numel(cfg.sampleStep) && ...
            step == cfg.sampleStep(nextSample)

        d43Sample(nextSample) = ...
            cfg.d43Scale*M(5)/M(4);

        nextSample = nextSample+1;
    end
end
end


%% =======================================================================
function [M,valid,info] = ...
    advanceAdaptive(M,DFnow,alphaMax,B,cfg)

remaining = cfg.dt;
h = cfg.dt;
attempts = 0;

valid = true;

info = struct;
info.halvings = 0;
info.acceptedSubsteps = 0;
info.advancedTime = 0;
info.reason = '';

while remaining > 10*eps(cfg.dt)
    attempts = attempts+1;

    if attempts > cfg.maximumSubsteps
        valid = false;
        info.reason = 'Maximum substep count exceeded.';
        return;
    end

    h = min(h,remaining);

    [rhsValid,dMdt,reason] = ...
        momentDerivative(M,DFnow,alphaMax,B,cfg);

    if ~rhsValid
        valid = false;
        info.reason = reason;
        return;
    end

    candidate = M+h*dMdt;

    if validMomentState(candidate,cfg)
        M = candidate;
        remaining = remaining-h;
        info.acceptedSubsteps = info.acceptedSubsteps+1;
        info.advancedTime = cfg.dt-remaining;

        if remaining > 0
            h = min(2*h,remaining);
        end
    else
        h = h/2;
        info.halvings = info.halvings+1;

        if h < cfg.minSubstep
            valid = false;
            info.reason = ...
                'Minimum substep reached before a valid moment update.';
            return;
        end
    end
end
end


%% =======================================================================
function [valid,dMdt,reason] = ...
    momentDerivative(M,DFnow,alphaMax,B,cfg)

valid = false;
dMdt = NaN(5,1);
reason = '';

try
    [w1,Xi1,sigma] = computeLogNormalNew(M);

    if ~isscalar(sigma) || ~isfinite(sigma) || ...
            ~isreal(sigma) || sigma <= cfg.sigmaMinimum
        reason = 'Invalid sigma from computeLogNormalNew.';
        return;
    end

    [w2,Xi2] = computeGaussWigert(cfg.Q,sigma);
catch ME
    reason = ME.message;
    return;
end

if any(~isfinite(w1)) || any(~isfinite(Xi1)) || ...
        any(~isfinite(w2)) || any(~isfinite(Xi2)) || ...
        ~isreal(w1) || ~isreal(Xi1) || ...
        ~isreal(w2) || ~isreal(Xi2) || ...
        any(Xi1 <= 0) || any(Xi2 <= 0)

    reason = 'Invalid quadrature weights or abscissas.';
    return;
end

w3 = w2;
Xi3 = Xi2;

n = cfg.n;
Q = cfg.Q;

dMdt = zeros(5,1);

for k = 1:5
    MOM1 = 0;
    MOM2 = 0;
    MOM3 = 0;
    MOM4 = 0;

    for i1 = 1:n
        for i2 = 1:Q
            r1 = Xi1(i1)*Xi2(i2);

            for i3 = 1:n
                for i4 = 1:Q
                    r2 = Xi1(i3)*Xi3(i4);

                    sizeRatio = min(r1,r2)/max(r1,r2);

                    collisionEfficiency = alphaMax* ...
                        exp(-cfg.x*(1-sizeRatio^DFnow)^2);

                    sizePenalty = ...
                        (r1*r2/(cfg.D0^2))^ ...
                        (DFnow*cfg.sizePenaltyMultiplier*cfg.y);

                    brownianKernel = ...
                        (2*cfg.kB*cfg.T/(3*cfg.mu))* ...
                        ((r1+r2)^2/(r1*r2));

                    shearKernelGain = ...
                        1.294*cfg.G*(r1+r2)^3/2;

                    shearKernelLoss = ...
                        1.294*cfg.G*(r1+r2)^3;

                    commonWeight = ...
                        w1(i1)*w2(i2)*w1(i3)*w3(i4);

                    MOM1 = MOM1+commonWeight* ...
                        (r1^DFnow+r2^DFnow)^ ...
                        ((k-1)/DFnow)* ...
                        collisionEfficiency/sizePenalty* ...
                        (brownianKernel+shearKernelGain);

                    MOM2 = MOM2+commonWeight* ...
                        r1^(k-1)* ...
                        collisionEfficiency/sizePenalty* ...
                        (brownianKernel+shearKernelLoss);
                end
            end

            breakupDenominator = ...
                (0.414*DFnow-0.211)* ...
                r1*cfg.epsilon;

            if ~isfinite(breakupDenominator) || ...
                    breakupDenominator <= 0
                reason = 'Invalid breakup denominator.';
                dMdt(:) = NaN;
                return;
            end

            breakupRate = sqrt(4/(15*pi))*cfg.G* ...
                exp(-B/breakupDenominator);

            MOM3 = MOM3+w1(i1)*w2(i2)* ...
                r1^(k-1)*breakupRate* ...
                2^((DFnow-(k-1))/DFnow);

            MOM4 = MOM4+w1(i1)*w2(i2)* ...
                r1^(k-1)*breakupRate;
        end
    end

    dMdt(k) = MOM1-MOM2+MOM3-MOM4;
end

if any(~isfinite(dMdt)) || ~isreal(dMdt)
    reason = 'Moment derivative became invalid.';
    dMdt(:) = NaN;
    return;
end

valid = true;
end


%% =======================================================================
function valid = validMomentState(M,cfg)

valid = numel(M)==5 && ...
    all(isfinite(M)) && isreal(M) && all(M > 0);

if ~valid
    return;
end

sigma2Estimate = log((M(1)*M(3))/(M(2)^2));

valid = isfinite(sigma2Estimate) && ...
    isreal(sigma2Estimate) && ...
    sigma2Estimate > cfg.sigmaMinimum^2;
end


%% =======================================================================
function R2 = coefficientOfDetermination(y,yhat)

denominator = sum((y-mean(y)).^2);

if denominator <= eps
    R2 = NaN;
else
    R2 = 1-sum((y-yhat).^2)/denominator;
end
end


%% =======================================================================
function z = boundedToUnbounded(p,lb,ub)

fraction = (p-lb)./(ub-lb);
fraction = min(max(fraction,1e-12),1-1e-12);
z = log(fraction./(1-fraction));
end


%% =======================================================================
function p = unboundedToBounded(z,lb,ub)

s = zeros(size(z));

positive = z >= 0;
s(positive) = 1./(1+exp(-z(positive)));

ez = exp(z(~positive));
s(~positive) = ez./(1+ez);

p = lb+(ub-lb).*s;
end
