function stop = checkStopCondition(theta, RMSE, state)
    stop = false;
    % Objective function value
    residuals = RMSE.fval;  % SSR is the objective value here
    if sum(residuals.^2) < 1e-8  % Check if SSR is below the threshold
        disp('Stopping optimization as SSR < 10^-8');
        stop = true;  % Stop optimization
    end
end


